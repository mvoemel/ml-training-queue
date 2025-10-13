import os
import asyncio
import redis.asyncio as redis
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import Job, GPU
from .docker_runner import DockerRunner
from ..logger import Logger

class JobScheduler:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self.docker_runner = DockerRunner()
        self.running_jobs = {}  # {gpu_id: job_id}
    
    async def init_redis(self):
        if not self.redis_client:
            self.redis_client = await redis.from_url(self.redis_url, decode_responses=True)
    
    async def add_job(self, job_id: int):
        await self.init_redis()
        db = SessionLocal()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            # Add to GPU-specific queue
            await self.redis_client.rpush(f"queue:gpu:{job.gpu_id}", job_id)
        db.close()
    
    async def remove_job(self, job_id: int):
        await self.init_redis()
        db = SessionLocal()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            # Remove from GPU-specific queue
            await self.redis_client.lrem(f"queue:gpu:{job.gpu_id}", 0, job_id)
        db.close()
    
    async def run(self):
        await self.init_redis()
        Logger.custom("Job scheduler started", "JOB_SCHEDULER", "blue")
        
        while True:
            try:
                await self.process_queues()
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                Logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(5)
    
    async def process_queues(self):
        db = SessionLocal()
        
        # Get all GPUs
        gpus = db.query(GPU).all()
        
        for gpu in gpus:
            # Check if GPU is busy
            if gpu.id in self.running_jobs:
                # Check if job is still running
                job = db.query(Job).filter(Job.id == self.running_jobs[gpu.id]).first()
                if job and job.status == "running":
                    continue  # GPU is busy
                else:
                    # Job finished, remove from running jobs
                    del self.running_jobs[gpu.id]
            
            # Get next job from queue
            job_id = await self.redis_client.lpop(f"queue:gpu:{gpu.id}")
            if job_id:
                job = db.query(Job).filter(Job.id == int(job_id)).first()
                if job and job.status == "pending":
                    # Start the job
                    asyncio.create_task(self.start_job(job, gpu))
                    self.running_jobs[gpu.id] = job.id
        
        db.close()
    
    async def start_job(self, job: Job, gpu: GPU):
        db = SessionLocal()
        
        try:
            # Update job status
            job.status = "running"
            db.add(job)
            db.commit()
            
            # Run job in Docker
            container_id = await self.docker_runner.run_job(job, gpu)
            
            # Update container ID
            job.container_id = container_id
            db.commit()
            
            # Wait for completion
            result = await self.docker_runner.wait_for_completion(container_id)
            
            # Update job status
            if result["status"] == "success":
                job.status = "completed"
            else:
                job.status = "failed"
                job.error_log = result.get("error", "Unknown error")
            
            from datetime import datetime
            job.completed_at = datetime.utcnow()
            db.commit()
            
        except Exception as e:
            job.status = "failed"
            job.error_log = str(e)
            from datetime import datetime
            job.completed_at = datetime.utcnow()
            db.commit()
            Logger.error(f"Error running job {job.id}: {e}")
        finally:
            # Remove from running jobs
            if gpu.id in self.running_jobs:
                del self.running_jobs[gpu.id]
            db.close()