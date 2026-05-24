from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.server import Server, ServerCreate, ServerUpdate
from app.models.server import Server as ServerModel
from app.services.balance_service import balance_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/servers", tags=["Servers"])

@router.get("/status")
async def get_servers_status(db: Session = Depends(get_db)):
    try:
        status = balance_service.get_server_status(db)
        return {
            "total_servers": len(status),
            "servers": status
        }
    except Exception as e:
        logger.error(f"Error getting server status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/", response_model=List[Server])
async def get_servers(db: Session = Depends(get_db)):
    try:
        servers = db.query(ServerModel).all()
        return [Server.from_db_model(s) for s in servers]
    except Exception as e:
        logger.error(f"Error getting servers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/", response_model=Server)
async def create_server(server: ServerCreate, db: Session = Depends(get_db)):
    try:
        existing = db.query(ServerModel).filter(ServerModel.name == server.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Server with this name already exists")

        db_server = ServerModel(**server.model_dump())
        db.add(db_server)
        db.commit()
        db.refresh(db_server)

        logger.info(f"Server created: {db_server.name}")
        return Server.from_db_model(db_server)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating server: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/{server_id}", response_model=Server)
async def update_server(server_id: int, server_update: ServerUpdate, db: Session = Depends(get_db)):
    try:
        db_server = db.query(ServerModel).filter(ServerModel.id == server_id).first()
        if not db_server:
            raise HTTPException(status_code=404, detail="Server not found")

        update_data = server_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_server, key, value)

        db.commit()
        db.refresh(db_server)

        logger.info(f"Server updated: {db_server.name}")
        return Server.from_db_model(db_server)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating server: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{server_id}")
async def delete_server(server_id: int, db: Session = Depends(get_db)):
    try:
        db_server = db.query(ServerModel).filter(ServerModel.id == server_id).first()
        if not db_server:
            raise HTTPException(status_code=404, detail="Server not found")

        db.delete(db_server)
        db.commit()

        logger.info(f"Server deleted: {db_server.name}")
        return {"message": f"Server {db_server.name} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting server: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
