import pandas as pd
import numpy as np
import pickle
import os
import json
import logging
from datetime import datetime
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from typing import Optional
from sqlalchemy.orm import Session
from app.models.ai_model import AIModel
from app.models.server import Server

logger = logging.getLogger(__name__)

MODEL_DIR = "models"
SCALER_FILE = os.path.join(MODEL_DIR, "scaler.pkl")
MODEL_FILE = os.path.join(MODEL_DIR, "model.pkl")

os.makedirs(MODEL_DIR, exist_ok=True)

class AIService:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_columns = [
            "Traffic Volume (Mbps)",
            "Network Latency (ms)",
            "Throughput (Mbps)",
            "Packet Loss (%)",
            "Signal Strength (dBm)",
            "Resource Allocation (%)",
            "Handover Success (0/1)"
        ]
        self.load_model()
    
    def evaluate_dataset(self, dataset_path: str, label_column: Optional[str] = None, use_heuristic: bool = False, db: Optional[Session] = None, servers_override: Optional[list] = None):
        """
        Evaluate current loaded model on a dataset without retraining.
        Returns metrics including accuracy (if labels provided), classification_report, confusion matrix,
        probability/confidence stats and sample predictions.
        """
        if self.model is None or self.scaler is None:
            self.load_model()

        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")

        df = pd.read_csv(dataset_path)
        if "Timestamp" in df.columns:
            df = df.drop("Timestamp", axis=1)

        X = df[self.feature_columns]

        # Determine labels if available
        y = None
        servers = None
        if servers_override is not None:
            servers = servers_override
        elif db is not None:
            servers = db.query(Server).all()

        if label_column and label_column in df.columns:
            y = df[label_column]
        elif servers and "server_id" in df.columns:
            y = df["server_id"]
        elif use_heuristic and servers:
            def assign_server_by_heuristic(df_local, servers_count=len(servers)):
                score = (-df_local["Network Latency (ms)"]) + (df_local["Signal Strength (dBm)"]) + (df_local["Resource Allocation (%)"])
                bins = np.linspace(score.min(), score.max(), servers_count + 1)
                labels = pd.cut(score, bins=bins, labels=range(servers_count), include_lowest=True).astype(int)
                return labels

            labels_idx = assign_server_by_heuristic(df)
            server_mapping = {i: server.id for i, server in enumerate(servers)}
            y = labels_idx.map(server_mapping)

        X_scaled = self.scaler.transform(X)
        probs = self.model.predict_proba(X_scaled)
        preds = self.model.predict(X_scaled)

        # confidence stats
        max_probs = np.max(probs, axis=1)
        mean_conf = float(np.mean(max_probs))
        low_conf_pct = float(np.mean(max_probs < 0.6))

        # entropy per sample
        eps = 1e-12
        entropies = -np.sum(probs * np.log(probs + eps), axis=1)
        mean_entropy = float(np.mean(entropies))

        metrics = {
            "mean_confidence": mean_conf,
            "low_confidence_percent": low_conf_pct,
            "mean_entropy": mean_entropy
        }

        if y is not None:
            try:
                acc = accuracy_score(y, preds)
                report = classification_report(y, preds, output_dict=True)
                conf_mat = confusion_matrix(y, preds)
                metrics.update({
                    "accuracy": float(acc),
                    "classification_report": report,
                    "confusion_matrix": conf_mat.tolist()
                })
            except Exception as e:
                logger.warning(f"Could not compute labeled metrics: {e}")

        # sample predictions
        sample_preds = []
        for i in range(min(10, len(df))):
            sample_preds.append({
                "index": int(i),
                "features": X.iloc[i].to_dict(),
                "predicted_class": int(preds[i]),
                "predicted_prob": float(max_probs[i]),
                "entropy": float(entropies[i])
            })

        return {
            "dataset_rows": len(df),
            "metrics": metrics,
            "sample_predictions": sample_preds
        }

    def load_model(self):
        try:
            if os.path.exists(MODEL_FILE) and os.path.exists(SCALER_FILE):
                with open(MODEL_FILE, 'rb') as f:
                    self.model = pickle.load(f)
                with open(SCALER_FILE, 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info("AI model and scaler loaded successfully")
            else:
                logger.warning("No trained model found. Please train a model first.")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            self.model = None
            self.scaler = None

    def save_model(self):
        try:
            with open(MODEL_FILE, 'wb') as f:
                pickle.dump(self.model, f)
            with open(SCALER_FILE, 'wb') as f:
                pickle.dump(self.scaler, f)
            logger.info("Model and scaler saved successfully")
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            raise

    def train_model(self, dataset_path: str, algorithm: str, db: Session, label_column: Optional[str] = None, use_heuristic: bool = False, servers_override: Optional[list] = None, persist_db: bool = True, min_accuracy: float = 0.70, auto_select_model: bool = True):
        try:
            logger.info(f"Starting model training with {algorithm} using {dataset_path}")

            if min_accuracy < 0 or min_accuracy > 1:
                raise ValueError("min_accuracy must be between 0 and 1.")

            if not os.path.exists(dataset_path):
                raise FileNotFoundError(f"Dataset not found: {dataset_path}")

            df = pd.read_csv(dataset_path)
            logger.info(f"Dataset loaded: {len(df)} rows")

            if "Timestamp" in df.columns:
                df = df.drop("Timestamp", axis=1)

            X = df[self.feature_columns]

            # Determine labels
            if label_column and label_column in df.columns:
                logger.info(f"Using provided label column: {label_column}")
                y = df[label_column]
            else:
                # Allow passing servers_override to avoid DB queries during testing or when DB models cause import issues
                if servers_override is not None:
                    servers = servers_override
                else:
                    servers = db.query(Server).all()
                if label_column and label_column not in df.columns:
                    logger.warning(f"Label column '{label_column}' not found in dataset. Falling back.")

                if servers and "server_id" in df.columns:
                    # If dataset already contains server_id and servers exist in DB, use it
                    logger.info("Using 'server_id' column from dataset as labels")
                    y = df["server_id"]
                elif use_heuristic and servers:
                    # Create labels by heuristic score and map to server ids
                    logger.info("Generating labels using heuristic (use_heuristic=True)")

                    def assign_server_by_heuristic(df_local, servers_count=len(servers)):
                        # Higher score means better candidate server
                        score = (-df_local["Network Latency (ms)"]) + (df_local["Signal Strength (dBm)"]) + (df_local["Resource Allocation (%)"])
                        bins = np.linspace(score.min(), score.max(), servers_count + 1)
                        labels = pd.cut(score, bins=bins, labels=range(servers_count), include_lowest=True).astype(int)
                        return labels

                    labels_idx = assign_server_by_heuristic(df)
                    server_mapping = {i: server.id for i, server in enumerate(servers)}
                    y = labels_idx.map(server_mapping)
                else:
                    # Unsafe default of index-based labels replaced by explicit error to avoid accidental random labels
                    raise ValueError("No valid label column provided and no heuristic enabled. Provide a 'label_column' or set 'use_heuristic=True' with servers available.")

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            def build_candidates(selected_algorithm: str):
                # Keep backward compatibility with existing frontend values while enforcing decision trees.
                aliases = {
                    "decision_tree": "decision_tree",
                    "random_forest": "decision_tree",
                    "gradient_boosting": "decision_tree",
                    "extra_trees": "decision_tree",
                    "auto": "decision_tree"
                }
                normalized_algorithm = aliases.get(selected_algorithm)
                if not normalized_algorithm:
                    raise ValueError(
                        f"Unknown algorithm: {selected_algorithm}. Use 'decision_tree'."
                    )
                return {
                    "decision_tree": DecisionTreeClassifier(
                        criterion="gini",
                        max_depth=12,
                        min_samples_split=8,
                        min_samples_leaf=4,
                        class_weight="balanced",
                        random_state=42
                    )
                }

            candidate_models = build_candidates(algorithm)
            ranking = []
            best_algorithm = None
            best_model = None
            best_accuracy = -1.0
            best_macro_f1 = -1.0
            best_report = None
            best_conf_matrix = None

            logger.info(f"Training {len(candidate_models)} candidate model(s)...")
            for candidate_name, candidate_model in candidate_models.items():
                candidate_model.fit(X_train_scaled, y_train)
                candidate_pred = candidate_model.predict(X_test_scaled)
                candidate_accuracy = float(accuracy_score(y_test, candidate_pred))
                candidate_macro_f1 = float(f1_score(y_test, candidate_pred, average="macro"))
                ranking.append({
                    "algorithm": candidate_name,
                    "accuracy": candidate_accuracy,
                    "macro_f1": candidate_macro_f1
                })

                # Select by macro_f1 first, then accuracy as tie-breaker
                if (candidate_macro_f1 > best_macro_f1) or (
                    candidate_macro_f1 == best_macro_f1 and candidate_accuracy > best_accuracy
                ):
                    best_algorithm = candidate_name
                    best_model = candidate_model
                    best_accuracy = candidate_accuracy
                    best_macro_f1 = candidate_macro_f1
                    best_report = classification_report(y_test, candidate_pred, output_dict=True)
                    best_conf_matrix = confusion_matrix(y_test, candidate_pred)

            ranking = sorted(ranking, key=lambda x: (x["macro_f1"], x["accuracy"]), reverse=True)
            accuracy = best_accuracy
            report = best_report
            conf_matrix = best_conf_matrix

            logger.info(f"Best model: {best_algorithm}. Accuracy: {accuracy:.4f}, Macro F1: {best_macro_f1:.4f}")

            if float(accuracy) < float(min_accuracy):
                raise ValueError(
                    f"Best model ({best_algorithm}) accuracy {float(accuracy):.4f} is below minimum threshold {float(min_accuracy):.2f}. "
                    "Improve data quality, tune labels, or lower the threshold."
                )

            self.model = best_model
            self.scaler = scaler
            self.save_model()

            model_version = f"v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

            if persist_db:
                db.query(AIModel).update({"is_active": False})

                ai_model = AIModel(
                    model_version=model_version,
                    algorithm=best_algorithm,
                    accuracy=float(accuracy),
                    training_samples=len(df),
                    is_active=True,
                    parameters=json.dumps({
                        "selected_algorithm": best_algorithm,
                        "requested_algorithm": algorithm,
                        "auto_select_model": bool(auto_select_model),
                        "criterion": "gini",
                        "max_depth": 12,
                        "min_samples_split": 8,
                        "min_samples_leaf": 4,
                        "class_weight": "balanced",
                        "test_size": 0.2,
                        "stratify": True,
                        "min_accuracy": float(min_accuracy)
                    }),
                    metrics=json.dumps({
                        "accuracy": float(accuracy),
                        "macro_f1": float(best_macro_f1),
                        "model_ranking": ranking,
                        "classification_report": {k: v for k, v in report.items() if k != 'accuracy'},
                        "confusion_matrix": conf_matrix.tolist()
                    })
                )
                db.add(ai_model)
                db.commit()
                db.refresh(ai_model)

            return {
                "model_version": model_version,
                "accuracy": float(accuracy),
                "algorithm": best_algorithm,
                "training_samples": len(df),
                "metrics": {
                    "accuracy": float(accuracy),
                    "macro_f1": float(best_macro_f1),
                    "min_accuracy_threshold": float(min_accuracy),
                    "auto_select_model": bool(auto_select_model),
                    "selected_algorithm": best_algorithm,
                    "model_ranking": ranking,
                    "test_samples": len(X_test),
                    "train_samples": len(X_train),
                    "classification_report": report,
                    "confusion_matrix": conf_matrix.tolist()
                }
            }

        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            raise

    def predict_server(self, metrics: dict, db: Session):
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained. Please train the model first.")

        try:
            features = pd.DataFrame([{
                "Traffic Volume (Mbps)": metrics["traffic_volume"],
                "Network Latency (ms)": metrics["network_latency"],
                "Throughput (Mbps)": metrics["throughput"],
                "Packet Loss (%)": metrics["packet_loss"],
                "Signal Strength (dBm)": metrics["signal_strength"],
                "Resource Allocation (%)": metrics["resource_allocation"],
                "Handover Success (0/1)": metrics["handover_success"]
            }])

            features_scaled = self.scaler.transform(features)

            prediction = self.model.predict(features_scaled)[0]
            probabilities = self.model.predict_proba(features_scaled)[0]
            confidence = float(max(probabilities))

            active_servers = db.query(Server).filter(Server.status == "active").all()
            if not active_servers:
                raise ValueError("No active servers available")

            server = db.query(Server).filter(Server.id == int(prediction), Server.status == "active").first()

            if not server:
                server = min(active_servers, key=lambda s: s.current_load)
                prediction = server.id
                confidence = 0.5

            all_predictions = {}
            for idx, prob in enumerate(probabilities):
                class_id = self.model.classes_[idx]
                srv = db.query(Server).filter(Server.id == int(class_id), Server.status == "active").first()
                if srv:
                    all_predictions[srv.name] = float(prob)

            return {
                "recommended_server_id": int(prediction),
                "recommended_server_name": server.name,
                "confidence": confidence,
                "all_predictions": all_predictions
            }

        except Exception as e:
            logger.error(f"Error making prediction: {str(e)}")
            raise

ai_service = AIService()
