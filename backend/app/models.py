from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    jobs = relationship("Job", back_populates="owner", cascade="all, delete-orphan")

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending")  # pending, running, completed, failed, cancelled
    gpu_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    dataset_path = Column(String, nullable=True)
    script_path = Column(String, nullable=True)
    requirements_path = Column(String, nullable=True)
    output_path = Column(String, nullable=True)
    
    container_id = Column(String, nullable=True)
    error_log = Column(Text, nullable=True)
    
    owner = relationship("User", back_populates="jobs")

class GPU(Base):
    __tablename__ = "gpus"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    memory = Column(Integer, nullable=False)  # in MB
    available = Column(Boolean, default=True)