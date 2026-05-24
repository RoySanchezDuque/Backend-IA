from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from app.database import Base


class AIModel(Base):
    __tablename__ = "ai_models"

    id = Column(Integer, primary_key=True, index=True)
    model_version = Column(String, nullable=False)
    algorithm = Column(String, nullable=False)
    accuracy = Column(Float, nullable=True)
    training_samples = Column(Integer, nullable=True)
    trained_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=False)
    parameters = Column(String, nullable=True)
    metrics = Column(String, nullable=True)
