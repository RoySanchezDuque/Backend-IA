from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.traffic import TrafficSendRequest, TrafficSendResponse
from app.services.balance_service import balance_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/traffic", tags=["Traffic"])

@router.post("/send", response_model=TrafficSendResponse)
async def send_traffic(request: TrafficSendRequest, db: Session = Depends(get_db)):
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

        server, confidence = balance_service.assign_server_ai(metrics, db)

        traffic_log = balance_service.log_traffic(metrics, server, confidence, db)

        return TrafficSendResponse(
            assigned_server_id=server.id,
            assigned_server_name=server.name,
            message=f"Traffic assigned to {server.name}",
            log_id=traffic_log.id
        )

    except ValueError as e:
        logger.error(f"Value error in send_traffic: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in send_traffic: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
