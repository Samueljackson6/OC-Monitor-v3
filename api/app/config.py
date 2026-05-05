"""
OC-Monitor v3.0 - 配置管理
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用信息
    APP_NAME: str = "OC-Monitor"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = False
    
    # API 配置
    API_PREFIX: str = "api/v1"
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///data/monitor.db"
    
    # Redis 配置（可选）
    REDIS_URL: Optional[str] = None
    
    # JWT 配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 小时
    
    # 初始管理员账户
    INITIAL_ADMIN_USERNAME: str = "admin"
    INITIAL_ADMIN_PASSWORD: str = "admin123"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
