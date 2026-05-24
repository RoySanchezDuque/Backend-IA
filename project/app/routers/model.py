from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.ai_model import ModelStatusResponse, AIModel as AIModelSchema
from app.models.ai_model import AIModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/model", tags=["Model"])

@router.get("/status", response_model=ModelStatusResponse)
async def get_model_status(db: Session = Depends(get_db)):
    try:
        active_model = db.query(AIModel).filter(AIModel.is_active == True).first()
        total_models = db.query(AIModel).count()

        status = "ready" if active_model else "no_model"

        response = ModelStatusResponse(
            active_model=AIModelSchema.model_validate(active_model) if active_model else None,
            total_models=total_models,
            status=status
        )

        return response

    except Exception as e:
        logger.error(f"Error getting model status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
