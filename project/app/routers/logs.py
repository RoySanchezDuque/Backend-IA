from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.traffic import TrafficLog
from app.services.balance_service import balance_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["Logs"])

@router.get("/", response_model=dict)
async def get_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    try:
        result = balance_service.get_traffic_logs(db, limit, offset)

        return {
            "total": result["total"],
            "limit": result["limit"],
            "offset": result["offset"],
            "logs": [TrafficLog.model_validate(log) for log in result["logs"]]
        }

    except Exception as e:
        logger.error(f"Error getting logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
