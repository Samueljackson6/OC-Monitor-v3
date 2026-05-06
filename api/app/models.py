"""
OC-Monitor v3.0 - database models.
"""
from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.sql import func
from app.database import Base


class ServerMetric(Base):
    __tablename__ = "server_metrics"
    id = Column(Integer, primary_key=True, index=True)
    cpu = Column(Float, nullable=False)
    memory = Column(Float, nullable=False)
    disk = Column(Float, nullable=False)
    gateway_status = Column(Boolean, default=False)
    timestamp = Column(Float, nullable=False, index=True)
    collected_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_timestamp", "timestamp"),)


class AgentMetric(Base):
    __tablename__ = "agent_metrics"
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(50), nullable=False, index=True)
    agent_name = Column(String(100))
    status = Column(String(20))
    memory_mb = Column("memory", Float)
    cpu_percent = Column("cpu", Float)
    timestamp = Column(Float, nullable=False)
    collected_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_agent_timestamp", "agent_id", "timestamp"),)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text)
    is_resolved = Column(Boolean, default=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
