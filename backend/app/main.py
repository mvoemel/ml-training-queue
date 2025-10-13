from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
import asyncio
from datetime import timedelta
import psutil

from .database import get_db, init_db
from .models import User, Job, GPU
from .schemas import UserCreate, UserResponse, Token, JobCreate, JobResponse, GPUResponse, GPUStats
from .auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from .services.job_scheduler import JobScheduler
from .services.docker_runner import DockerRunner
from .services.gpu_monitor import GPUMonitor

app = FastAPI(title="ML Training Queue")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
job_scheduler = JobScheduler() # starts its own instance of the DockerRunner()
docker_runner = DockerRunner()
gpu_monitor = GPUMonitor()

# Directories
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./data/uploads")
JOBS_DIR = os.getenv("JOBS_DIR", "./data/jobs")
OUTPUTS_DIR = os.getenv("OUTPUTS_DIR", "./data/outputs")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(JOBS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

@app.on_event("startup")
async def startup_event():
    init_db()
    
    # Initialize GPUs if not already done
    db = next(get_db())
    if db.query(GPU).count() == 0:
        gpus = gpu_monitor.get_available_gpus()
        for gpu_info in gpus:
            gpu = GPU(
                id=gpu_info['id'],
                name=gpu_info['name'],
                memory=gpu_info['memory'],
                available=True
            )
            db.add(gpu)
        db.commit()
    db.close()
    
    # Start scheduler
    asyncio.create_task(job_scheduler.run())



# ============ AUTH ENDPOINTS ============

@app.post("/api/auth/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Only allow registration if no users exist
    if db.query(User).count() > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled. Only the first user can register."
        )
    
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/auth/login", response_model=Token)
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Token holds following data: {"sub": "<username>", "exp": <expiration_time>"}
    access_token = create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/check")
def check_registration_status(db: Session = Depends(get_db)):
    user_count = db.query(User).count()
    return {"can_register": user_count == 0, "user_count": user_count}



# ============ USER MANAGEMENT ============

@app.get("/api/users", response_model=List[UserResponse])
def get_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(User).all()

@app.post("/api/users", response_model=UserResponse)
def create_user(
    user: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.delete("/api/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}



# ============ GPU ENDPOINTS ============

@app.get("/api/gpus", response_model=List[GPUResponse])
def get_gpus(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(GPU).all()

@app.get("/api/gpus/{gpu_id}/stats", response_model=GPUStats)
def get_gpu_stats(
    gpu_id: int,
    current_user: User = Depends(get_current_user)
):
    stats = gpu_monitor.get_gpu_stats(gpu_id)
    if not stats:
        raise HTTPException(status_code=404, detail="GPU not found")
    return stats



# ============ JOB ENDPOINTS ============

@app.get("/api/jobs", response_model=List[JobResponse])
def get_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Job).order_by(Job.created_at.desc()).all()

@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.post("/api/jobs", response_model=JobResponse)
async def create_job(
    name: str = Form(...),
    gpu_id: int = Form(...),
    dataset: UploadFile = File(...),
    script: UploadFile = File(...),
    requirements: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create job entry
    job = Job(
        name=name,
        user_id=current_user.id,
        gpu_id=gpu_id,
        status="pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Create job directory
    job_dir = os.path.join(JOBS_DIR, str(job.id))
    os.makedirs(job_dir, exist_ok=True)
    
    # Save files with chunked upload for large files
    dataset_path = os.path.join(job_dir, "dataset.zip")
    script_path = os.path.join(job_dir, "train.py")
    requirements_path = os.path.join(job_dir, "requirements.txt")
    
    # Chunked upload for large files
    async def save_upload_file(upload_file: UploadFile, destination: str):
        with open(destination, "wb") as buffer:
            while chunk := await upload_file.read(1024 * 1024):  # 1MB chunks
                buffer.write(chunk)
    
    await save_upload_file(dataset, dataset_path)
    await save_upload_file(script, script_path)
    await save_upload_file(requirements, requirements_path)
    
    # Update job with file paths
    job.dataset_path = dataset_path
    job.script_path = script_path
    job.requirements_path = requirements_path
    job.output_path = os.path.join(OUTPUTS_DIR, str(job.id))
    
    db.commit()
    db.refresh(job)
    
    # Add to queue
    await job_scheduler.add_job(job.id)
    
    return job

@app.delete("/api/jobs/{job_id}")
async def cancel_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status == "running":
        # Stop container
        if job.container_id:
            await docker_runner.stop_container(job.container_id)
        job.status = "cancelled"
    elif job.status == "pending":
        job.status = "cancelled"
        await job_scheduler.remove_job(job.id)
    
    db.commit()
    return {"message": "Job cancelled"}

@app.get("/api/jobs/{job_id}/logs")
async def get_job_logs(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job.container_id:
        return {"logs": "No logs available yet"}
    
    logs = await docker_runner.get_container_logs(job.container_id)
    return {"logs": logs}

@app.get("/api/jobs/{job_id}/download")
def download_output(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    if not job.output_path or not os.path.exists(job.output_path):
        raise HTTPException(status_code=404, detail="Output not found")
    
    # Create zip of output directory
    output_zip = f"{job.output_path}.zip"
    if not os.path.exists(output_zip):
        shutil.make_archive(job.output_path, 'zip', job.output_path)
    
    return FileResponse(
        output_zip,
        media_type="application/zip",
        filename=f"{job.name}_output.zip"
    )



# ============ WEBSOCKET FOR REAL-TIME UPDATES ============

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, job_id: int):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, job_id: int):
        if job_id in self.active_connections:
            self.active_connections[job_id].remove(websocket)
    
    async def broadcast(self, job_id: int, message: dict):
        if job_id in self.active_connections:
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

@app.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: int):
    await manager.connect(websocket, job_id)
    try:
        db = next(get_db())
        while True:
            # Send job status and GPU stats every 2 seconds
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                gpu_stats = gpu_monitor.get_gpu_stats(job.gpu_id)
                logs = ""
                if job.container_id:
                    logs = await docker_runner.get_container_logs(job.container_id, tail=50)
                
                await websocket.send_json({
                    "status": job.status,
                    "gpu_stats": gpu_stats,
                    "logs": logs
                })
            
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)
    finally:
        db.close()