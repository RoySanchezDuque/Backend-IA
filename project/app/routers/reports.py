from datetime import datetime, timedelta
from statistics import mean
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.traffic_log import TrafficLog


router = APIRouter(prefix="/reports", tags=["Reports"])


class GenerateReportRequest(BaseModel):
    period: Literal["diario", "semanal", "mensual"] = "mensual"


def _period_start(period: str, now: datetime) -> datetime:
    if period == "diario":
        return now - timedelta(days=1)
    if period == "semanal":
        return now - timedelta(days=7)
    return now - timedelta(days=30)


def _build_report(db: Session, period: str, report_id: int) -> dict:
    now = datetime.utcnow()
    start = _period_start(period, now)

    logs = (
        db.query(TrafficLog)
        .filter(TrafficLog.timestamp >= start)
        .order_by(TrafficLog.timestamp.desc())
        .all()
    )

    if logs:
        avg_traffic = float(mean(log.traffic_volume for log in logs))
        avg_latency = float(mean(log.network_latency for log in logs))
        confidence_values = [
            float(log.prediction_confidence)
            for log in logs
            if log.prediction_confidence is not None
        ]
        ia_efficiency = float(mean(confidence_values) * 100) if confidence_values else 0.0
        incidents = sum(
            1
            for log in logs
            if log.network_latency >= 150
            or log.packet_loss >= 2
            or log.assigned_server_id is None
        )
    else:
        avg_traffic = 0.0
        avg_latency = 0.0
        ia_efficiency = 0.0
        incidents = 0

    return {
        "id": report_id,
        "fecha": now.date().isoformat(),
        "tipoInforme": period,
        "metricas": {
            "traficoPromedio": round(avg_traffic, 2),
            "latenciaPromedio": round(avg_latency, 2),
            "eficienciaIA": round(ia_efficiency, 2),
            "incidentes": int(incidents),
        },
        "url": f"/reports/{period}/{now.date().isoformat()}",
    }


@router.get("/", response_model=dict)
async def get_reports(db: Session = Depends(get_db)):
    try:
        periods = ["diario", "semanal", "mensual"]
        reports = [_build_report(db, period, idx + 1) for idx, period in enumerate(periods)]
        return {"reports": reports}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(exc)}")


@router.post("/generate", response_model=dict)
async def generate_report(request: GenerateReportRequest, db: Session = Depends(get_db)):
    try:
        report = _build_report(db, request.period, int(datetime.utcnow().timestamp()))
        return {"message": "Report generated successfully", "report": report}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(exc)}")
