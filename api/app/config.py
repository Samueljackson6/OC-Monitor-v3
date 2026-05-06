"""
OC-Monitor v3.0 - application settings.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "OC-Monitor"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    API_PREFIX: str = "api/v1"
    CORS_ORIGINS: str = "*"
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/monitor.db"
    REDIS_URL: Optional[str] = None
    SECRET_KEY: str = "change-me-in-env"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    AUTH_REQUIRED: bool = True
    INITIAL_ADMIN_USERNAME: str = "admin"
    INITIAL_ADMIN_PASSWORD: str = ""
    INGEST_TOKEN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"
    COLLECTOR_INTERVAL_MIN: int = 5
    COLLECTOR_INTERVAL_MAX: int = 60
    DATA_RETENTION_DAYS: int = 30
    RESOLVED_ALERT_RETENTION_DAYS: int = 30
    ALERT_CPU_THRESHOLD: float = 80.0
    ALERT_MEMORY_THRESHOLD: float = 85.0
    ALERT_DISK_THRESHOLD: float = 90.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
