import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.schemas.settings import SystemSettings


router = APIRouter(prefix="/settings", tags=["Settings"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_FILE = PROJECT_ROOT / "system_settings.json"


def _default_settings() -> SystemSettings:
    return SystemSettings()


def _read_settings() -> SystemSettings:
    if not SETTINGS_FILE.exists():
        settings = _default_settings()
        _write_settings(settings)
        return settings

    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return SystemSettings(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not read settings: {str(e)}")


def _write_settings(settings: SystemSettings) -> None:
    try:
        with SETTINGS_FILE.open("w", encoding="utf-8") as f:
            json.dump(settings.model_dump(), f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save settings: {str(e)}")


@router.get("", response_model=SystemSettings)
async def get_settings():
    return _read_settings()


@router.put("", response_model=SystemSettings)
async def update_settings(payload: SystemSettings):
    _write_settings(payload)
    return payload


@router.post("/reset", response_model=SystemSettings)
async def reset_settings():
    settings = _default_settings()
    _write_settings(settings)
    return settings
