from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine, Base, SessionLocal
from app.routers import traffic, servers, ai, logs, model, reports, settings
from app.models.server import Server

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def init_database():
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        server_count = db.query(Server).count()
        if server_count == 0:
            logger.info("Creating default servers...")
            default_servers = [
                Server(
                    name="Server-1",
                    ip_address="192.168.1.10",
                    status="active",
                    current_load=random.uniform(20, 50),  # Iniciar con carga aleatoria
                    max_capacity=100.0
                ),
                Server(
                    name="Server-2",
                    ip_address="192.168.1.11",
                    status="active",
                    current_load=random.uniform(20, 50),
                    max_capacity=100.0
                ),
                Server(
                    name="Server-3",
                    ip_address="192.168.1.12",
                    status="active",
                    current_load=random.uniform(20, 50),
                    max_capacity=100.0
                )
            ]
            db.add_all(default_servers)
            db.commit()
            logger.info(f"Created {len(default_servers)} default servers with initial loads")
        else:
            logger.info(f"Found {server_count} existing servers")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        db.rollback()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Load Balancer Backend...")
    init_database()
    yield
    logger.info("Shutting down Load Balancer Backend...")

app = FastAPI(
    title="Sistema de Balanceo de Carga basado en IA",
    description="Backend API para sistema de balanceo de carga con predicción basada en IA",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS origins from environment so deployments (Vercel, Render, etc.)
# can set allowed origins without changing code. If ALLOWED_ORIGINS is not set,
# fall back to local development origins.
allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
if allowed_origins_env:
    # Allow comma-separated list in env var, e.g. "https://app.vercel.app,https://api.example.com"
    allow_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
else:
    allow_origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Middleware para aplicar decaimiento natural de carga
@app.middleware("http")
async def apply_load_decay(request, call_next):
    """Aplica decaimiento pasivo a las cargas de todos los servidores"""
    db = None
    try:
        db = SessionLocal()
        servers = db.query(Server).all()
        for server in servers:
            # Decay ligero: 0.1-0.5% por request
            decay = random.uniform(0.1, 0.5)
            server.current_load = max(0.0, server.current_load - decay)
        db.commit()
    except Exception as e:
        if db:
            db.rollback()
        logger.debug(f"Decay middleware error: {e}")
    finally:
        if db:
            db.close()
    
    response = await call_next(request)
    return response

app.include_router(traffic.router)
app.include_router(servers.router)
app.include_router(ai.router)
app.include_router(logs.router)
app.include_router(model.router)
app.include_router(reports.router)
app.include_router(settings.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "message": "Datos de entrada inválidos",
            "errors": exc.errors(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.detail if isinstance(exc.detail, str) else "Error en la solicitud",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error at {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "message": "Error interno del servidor",
            "path": str(request.url.path)
        }
    )

@app.get("/")
async def root():
    return {
        "message": "Sistema de Balanceo de Carga basado en IA - API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    db = None
    try:
        db = SessionLocal()
        server_count = db.query(Server).count()
        return {
            "status": "healthy",
            "service": "load-balancer-api",
            "database": "connected",
            "servers_count": server_count
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "load-balancer-api",
                "error": str(e)
            }
        )
    finally:
        if db:
            db.close()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
