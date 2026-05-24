from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.ai_model import TrainRequest, TrainResponse
from app.schemas.ai_model import EvaluateRequest, EvaluateResponse
from app.schemas.traffic import PredictionRequest, PredictionResponse
from app.services.ai_service import ai_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/train", response_model=TrainResponse)
async def train_model(request: TrainRequest, db: Session = Depends(get_db)):
    try:
        logger.info(f"Training request received: {request.dataset_path}, {request.algorithm}")
        logger.info(f"Train options: label_column={request.label_column}, use_heuristic={request.use_heuristic}")

        result = ai_service.train_model(
            request.dataset_path,
            request.algorithm,
            db,
            label_column=request.label_column,
            use_heuristic=request.use_heuristic,
            min_accuracy=request.min_accuracy,
            auto_select_model=request.auto_select_model
        )

        return TrainResponse(
            message="Model trained successfully",
            model_version=result["model_version"],
            accuracy=result["accuracy"],
            training_samples=result["training_samples"],
            metrics=result["metrics"]
        )

    except FileNotFoundError as e:
        logger.error(f"Dataset not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"Invalid training parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error training model: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_dataset(request: EvaluateRequest, db: Session = Depends(get_db)):
    try:
        logger.info(f"Evaluation request received: {request.dataset_path}, use_heuristic={request.use_heuristic}, label_column={request.label_column}")

        result = ai_service.evaluate_dataset(request.dataset_path, label_column=request.label_column, use_heuristic=request.use_heuristic, db=db)

        return EvaluateResponse(
            message="Evaluation completed",
            dataset_rows=result["dataset_rows"],
            metrics={
                **result["metrics"],
                "sample_predictions": result.get("sample_predictions", [])
            }
        )

    except FileNotFoundError as e:
        logger.error(f"Dataset not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error during evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/predict", response_model=PredictionResponse)
async def predict_server(request: PredictionRequest, db: Session = Depends(get_db)):
    try:
        metrics = {
            "traffic_volume": request.traffic_volume,
            "network_latency": request.network_latency,
            "throughput": request.throughput,
            "packet_loss": request.packet_loss,
            "signal_strength": request.signal_strength,
            "resource_allocation": request.resource_allocation,
            "handover_success": request.handover_success
        }

        prediction = ai_service.predict_server(metrics, db)

        return PredictionResponse(
            recommended_server_id=prediction["recommended_server_id"],
            recommended_server_name=prediction["recommended_server_name"],
            confidence=prediction["confidence"],
            all_predictions=prediction["all_predictions"]
        )

    except ValueError as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error making prediction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
