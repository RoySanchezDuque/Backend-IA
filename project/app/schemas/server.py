from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class ServerBase(BaseModel):
    name: str
    ip_address: str
    status: str = "active"
    current_load: float = 0.0
    max_capacity: float = 100.0

class ServerCreate(ServerBase):
    pass

class ServerUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    status: Optional[str] = None
    current_load: Optional[float] = None
    max_capacity: Optional[float] = None

class Server(BaseModel):
    id: int
    name: str
    ip_address: str
    port: int = 8000
    status: str
    load_percentage: float
    latency_ms: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_db_model(cls, db_server):
        """Convert DB model to schema, mapping fields as needed"""
        return cls(
            id=db_server.id,
            name=db_server.name,
            ip_address=db_server.ip_address,
            port=8000,
            status=db_server.status,
            load_percentage=db_server.current_load,
            latency_ms=0.0,
            created_at=getattr(db_server, 'created_at', None),
            updated_at=db_server.updated_at
        )

