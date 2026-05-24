from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict

class AIModelBase(BaseModel):
    model_version: str
    algorithm: str
    accuracy: float
    training_samples: int

class AIModelCreate(AIModelBase):
    parameters: Optional[str] = None
    metrics: Optional[str] = None

class AIModel(AIModelBase):
    id: int
    trained_at: datetime
    is_active: bool
    parameters: Optional[str] = None
    metrics: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

class TrainRequest(BaseModel):
    dataset_path: str = "6G_dataset_final.csv"
    algorithm: str = "decision_tree"
    # Intentamos usar columna 'server_id' si existe; de lo contrario, caemos a heurística
    label_column: Optional[str] = "server_id"
    use_heuristic: Optional[bool] = True
    min_accuracy: float = 0.70
    auto_select_model: bool = True

class TrainResponse(BaseModel):
    message: str
    model_version: str
    accuracy: float
    training_samples: int
    metrics: Dict


class EvaluateRequest(BaseModel):
    dataset_path: str = "6G_dataset_final.csv"
    label_column: Optional[str] = None
    use_heuristic: Optional[bool] = False


class EvaluateResponse(BaseModel):
    message: str
    dataset_rows: int
    metrics: Dict

class ModelStatusResponse(BaseModel):
    active_model: Optional[AIModel] = None
    total_models: int
    status: str
