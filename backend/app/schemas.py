from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class JobCreate(BaseModel):
    name: str
    gpu_id: int
    cpu_cores: int

class JobResponse(BaseModel):
    id: int
    name: str
    user_id: int
    status: str
    gpu_id: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    container_id: Optional[str] = None
    error_log: Optional[str] = None
    
    class Config:
        from_attributes = True

class GPUResponse(BaseModel):
    id: int
    name: str
    memory: int
    available: bool
    
    class Config:
        from_attributes = True

class GPUStats(BaseModel):
    gpu_id: int
    utilization: float
    memory_used: int
    memory_total: int
    temperature: float