"""
OC-Monitor v3.0 - 数据库模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ServerMetric(Base):
    """服务器指标表"""
    __tablename__ = "server_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    cpu = Column(Float, nullable=False)
    memory = Column(Float, nullable=False)
    disk = Column(Float, nullable=False)
    gateway_status = Column(Boolean, default=False)
    timestamp = Column(Float, nullable=False, index=True)
    collected_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_timestamp', 'timestamp'),
    )


class AgentMetric(Base):
    """Agent 指标表"""
    __tablename__ = "agent_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(50), nullable=False, index=True)
    agent_name = Column(String(100))
    status = Column(String(20))  # online, offline
    memory_mb = Column(Float)
    cpu_percent = Column(Float)
    timestamp = Column(Float, nullable=False)
    collected_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_agent_timestamp', 'agent_id', 'timestamp'),
    )


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class Alert(Base):
    """告警表"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(50), nullable=False)  # cpu, memory, disk, gateway
    severity = Column(String(20), nullable=False)  # critical, warning, info
    title = Column(String(200), nullable=False)
    message = Column(Text)
    is_resolved = Column(Boolean, default=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
