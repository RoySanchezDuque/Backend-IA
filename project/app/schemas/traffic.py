from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional

class TrafficMetrics(BaseModel):
    traffic_volume: float = Field(..., ge=0, le=10000)
    network_latency: float = Field(..., ge=0, le=1000)
    throughput: float = Field(..., ge=0, le=10000)
    packet_loss: float = Field(..., ge=0, le=100)
    signal_strength: float = Field(..., ge=-150, le=0)
    resource_allocation: float = Field(..., ge=0, le=100)
    handover_success: float = Field(..., ge=0, le=1)

class TrafficSendRequest(TrafficMetrics):
    pass

class TrafficSendResponse(BaseModel):
    assigned_server_id: int
    assigned_server_name: str
    message: str
    log_id: int

class TrafficLog(BaseModel):
    traffic_volume: float
    network_latency: float
    throughput: float
    packet_loss: float
    signal_strength: float
    resource_allocation: float
    handover_success: float
    id: int
    timestamp: datetime
    assigned_server_id: Optional[int] = None
    assigned_server_name: Optional[str] = None
    prediction_confidence: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class PredictionRequest(TrafficMetrics):
    pass

class PredictionResponse(BaseModel):
    recommended_server_id: int
    recommended_server_name: str
    confidence: float
    all_predictions: dict
