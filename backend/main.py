from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import redis
import json
import uuid
import os
import shutil
import asyncio
from datetime import datetime
from typing import Optional
import pynvml
import aiofiles
import zipfile
from pathlib import Path
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
r = redis.from_url(REDIS_URL, decode_responses=True)

# Use different paths for Docker vs local development
if os.path.exists("/app"):
    DATA_DIR = "/app/data"
else:
    # Local development
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

UPLOADS_DIR = f"{DATA_DIR}/uploads"
JOBS_DIR = f"{DATA_DIR}/jobs"
OUTPUTS_DIR = f"{DATA_DIR}/outputs"

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(JOBS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)


def get_gpu_info():
    """Get information about available NVIDIA GPUs"""
    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        gpus = []
        
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            
            gpus.append({
                "id": i,
                "name": name,
                "memory_total": memory_info.total,
                "memory_used": memory_info.used,
                "memory_free": memory_info.free,
                "utilization": utilization.gpu
            })
        
        return gpus
    except Exception as e:
        return []


@app.get("/api/gpus")
async def get_gpus():
    """Get list of available GPUs"""
    return {"gpus": get_gpu_info()}


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    resource: str = Form(...),
    docker_image: str = Form(...)
):
    """Create a new training job"""
    job_id = str(uuid.uuid4())
    job_name = file.filename.replace(".zip", "")
    
    # Save uploaded file in chunks to avoid memory issues
    upload_path = f"{UPLOADS_DIR}/{job_id}.zip"
    async with aiofiles.open(upload_path, "wb") as f:
        while chunk := await file.read(10 * 1024 * 1024):  # Read 10MB at a time
            await f.write(chunk)
    
    # Create job metadata
    job_data = {
        "id": job_id,
        "name": job_name,
        "status": "pending",
        "resource": resource,
        "docker_image": docker_image,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "error": None
    }
    
    # Store in Redis
    r.set(f"job:{job_id}", json.dumps(job_data))
    r.lpush("queue:pending", job_id)
    
    return {"job_id": job_id, "status": "pending"}


@app.get("/api/jobs")
async def get_jobs():
    """Get all jobs"""
    jobs = []
    for key in r.scan_iter("job:*"):
        job_data = json.loads(r.get(key))
        jobs.append(job_data)
    
    # Sort by creation date (newest first)
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    return {"jobs": jobs}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get specific job details"""
    job_key = f"job:{job_id}"
    job_data = r.get(job_key)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = json.loads(job_data)
    
    # Get GPU info if job is using GPU
    gpu_info = None
    if job["status"] == "running" and job["resource"].startswith("gpu:"):
        gpu_id = int(job["resource"].split(":")[1])
        gpus = get_gpu_info()
        if gpu_id < len(gpus):
            gpu_info = gpus[gpu_id]
    
    return {
        "job": job,
        "gpu_info": gpu_info
    }


@app.get("/api/jobs/{job_id}/logs")
async def get_job_logs(job_id: str):
    """Get job console logs"""
    log_file = f"{JOBS_DIR}/{job_id}/output.log"
    
    if not os.path.exists(log_file):
        return {"logs": ""}
    
    with open(log_file, "r") as f:
        logs = f.read()
    
    return {"logs": logs}


@app.get("/api/jobs/{job_id}/logs/stream")
async def stream_job_logs(job_id: str):
    """Stream job console logs"""
    log_file = f"{JOBS_DIR}/{job_id}/output.log"
    
    async def log_generator():
        last_size = 0
        while True:
            if os.path.exists(log_file):
                current_size = os.path.getsize(log_file)
                if current_size > last_size:
                    with open(log_file, "r") as f:
                        f.seek(last_size)
                        new_content = f.read()
                        last_size = current_size
                        yield f"data: {json.dumps({'logs': new_content})}\n\n"
            
            # Check if job is still running
            job_data = r.get(f"job:{job_id}")
            if job_data:
                job = json.loads(job_data)
                if job["status"] not in ["pending", "running"]:
                    break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(log_generator(), media_type="text/event-stream")


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a job"""
    job_key = f"job:{job_id}"
    job_data = r.get(job_key)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = json.loads(job_data)
    
    if job["status"] not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    
    # Update status
    job["status"] = "cancelled"
    job["completed_at"] = datetime.now().isoformat()
    r.set(job_key, json.dumps(job))
    
    # Remove from pending queue if present
    r.lrem("queue:pending", 0, job_id)
    
    # If running, stop the container
    if job.get("resource"):
        r.delete(f"resource:{job['resource']}")
    
    # Try to stop the Docker container if it's running
    container_id = r.get(f"container:{job_id}")
    if container_id:
        try:
            import docker
            docker_client = docker.from_env()
            container = docker_client.containers.get(container_id)
            container.stop(timeout=5)
            container.remove()
            print(f"Stopped and removed container {container_id[:12]} for job {job_id}")
        except Exception as e:
            print(f"Error stopping container: {e}")
            # Continue anyway, worker will handle it
        finally:
            r.delete(f"container:{job_id}")
    
    return {"status": "cancelled"}


@app.get("/api/jobs/{job_id}/download")
async def download_job_output(job_id: str):
    """Download trained model"""
    output_dir = Path(f"{OUTPUTS_DIR}/{job_id}")
    
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Output not found")
    
    def generate_zip():
        # Create an in-memory buffer for streaming
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in output_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(output_dir)
                    zip_file.write(file_path, arcname)
        
        zip_buffer.seek(0)
        
        # Stream the zip file in chunks
        while chunk := zip_buffer.read(8192):
            yield chunk
    
    return StreamingResponse(
        generate_zip(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={job_id}_output.zip"}
    )


@app.get("/")
async def root():
    return {"status": "ok"}