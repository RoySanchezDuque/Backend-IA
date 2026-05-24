from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class TrafficLog(Base):
    __tablename__ = "traffic_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    traffic_volume = Column(Float, default=0.0)
    network_latency = Column(Float, default=0.0)
    throughput = Column(Float, default=0.0)
    packet_loss = Column(Float, default=0.0)
    signal_strength = Column(Float, default=0.0)
    resource_allocation = Column(Float, default=0.0)
    handover_success = Column(Float, default=0.0)

    assigned_server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    assigned_server_name = Column(String, nullable=True)
    prediction_confidence = Column(Float, nullable=True)

    server = relationship("Server", back_populates="traffic_logs")
