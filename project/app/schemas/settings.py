from pydantic import BaseModel, Field, model_validator
from typing import Literal


class SystemSettings(BaseModel):
    algorithm: Literal["ia", "roundrobin", "leastconnections"] = "ia"
    automatic_mode: bool = True
    update_frequency_sec: int = Field(default=5, ge=1, le=10)
    notifications_enabled: bool = True
    warning_threshold: int = Field(default=60, ge=30, le=90)
    critical_threshold: int = Field(default=80, ge=35, le=100)
    retention_days: int = Field(default=30, ge=7, le=365)
    api_endpoint: str = "https://api.balanceo-ia.edu/v1"

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.critical_threshold <= self.warning_threshold:
            raise ValueError("critical_threshold must be greater than warning_threshold")
        return self
