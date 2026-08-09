"""
Jarvis OS - Database Models
"""
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from jarvis.database.core import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    role = Column(String(20), default="user")  # admin, user, viewer
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    projects = relationship("Project", back_populates="owner")
    api_keys = relationship("APIKey", back_populates="user")
    oauth_accounts = relationship("OAuthAccount", back_populates="user")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    settings = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="projects")


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    encrypted_key = Column(String, nullable=False)
    provider = Column(String(50), nullable=False)  # openai, anthropic, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="api_keys")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(JSON, default={})
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)
    account_id = Column(String(100), nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    label = Column(String(50), nullable=True)  # e.g., "Work", "Personal"
    scopes = Column(String, nullable=True)  # Space-separated granted scopes
    metadata_ = Column("metadata", JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="oauth_accounts")


class MemoryNode(Base):
    __tablename__ = "memory_nodes"

    id = Column(String(50), primary_key=True, index=True)
    content = Column(Text, nullable=False)
    memory_type = Column(String(50), index=True, nullable=False)
    metadata_ = Column("metadata", JSON, default={})
    timestamp = Column(Float, nullable=False)
    importance = Column(Float, default=0.5)
    embedding = Column(Vector(384))
