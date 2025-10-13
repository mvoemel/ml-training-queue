import docker
import asyncio
import os
import zipfile
from ..models import Job, GPU
from ..logger import Logger

class DockerRunner:
    def __init__(self):
        # Initialize Docker client compatible with Docker 28+
        try:
            # Try direct socket connection first
            self.client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
            # Test connection
            self.client.ping()
            Logger.custom("Docker client connected successfully", "DOCKER_RUNNER", "cyan")
            
        except Exception as e:
            Logger.error(f"Docker socket connection failed: {e}")
            try:
                # Fallback to environment detection
                self.client = docker.from_env()
                self.client.ping()
                Logger.custom("Docker client connected via environment", "DOCKER_RUNNER", "cyan")
            except Exception as e2:
                Logger.error(f"Docker environment connection also failed: {e2}")
                raise Exception(f"Cannot connect to Docker daemon: {e2}")
    
    async def run_job(self, job: Job, gpu: GPU):
        """Run a training job in a Docker container"""
        
        # Extract dataset
        job_dir = os.path.dirname(job.script_path)
        dataset_dir = os.path.join(job_dir, "dataset")
        os.makedirs(dataset_dir, exist_ok=True)
        
        with zipfile.ZipFile(job.dataset_path, 'r') as zip_ref:
            zip_ref.extractall(dataset_dir)
        
        # Create output directory
        os.makedirs(job.output_path, exist_ok=True)
        
        # Determine base image based on requirements
        base_image = await self._determine_base_image(job.requirements_path)
        
        # Create Dockerfile
        dockerfile_content = f"""FROM {base_image}
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY dataset ./dataset
COPY train.py .
CMD ["python", "train.py"]
"""
        dockerfile_path = os.path.join(job_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)
        
        # Build image
        image_tag = f"ml-training-job-{job.id}"
        Logger.custom(f"Building image for job {job.id}...", "DOCKER_RUNNER", "cyan")
        
        try:
            # Use low-level API client for building
            api_client = self.client.api
            build_logs = api_client.build(
                path=job_dir,
                tag=image_tag,
                rm=True,
                decode=True
            )
            
            for log in build_logs:
                if 'stream' in log:
                    Logger.custom(log['stream'].strip(),f"JOB_{job.id}", "magenta")
                elif 'error' in log:
                    raise docker.errors.BuildError(log['error'], build_logs)
                    
        except Exception as e:
            Logger.error(f"Build error: {e}")
            raise
        
        # Run container
        Logger.custom(f"Starting container for job {job.id} on GPU {gpu.id}...", "DOCKER_RUNNER", "cyan")
        
        container = self.client.containers.run(
            image_tag,
            detach=True,
            device_requests=[
                docker.types.DeviceRequest(
                    device_ids=[str(gpu.id)],
                    capabilities=[['gpu']]
                )
            ],
            cpu_count=job.cpu_cores,
            volumes={
                job.output_path: {'bind': '/workspace/output', 'mode': 'rw'}
            },
            name=f"job-{job.id}"
        )
        
        return container.id
    
    async def _determine_base_image(self, requirements_path: str) -> str:
        """Determine which base image to use based on requirements"""
        with open(requirements_path, 'r') as f:
            content = f.read().lower()
        
        if 'tensorflow' in content:
            return "tensorflow/tensorflow:latest-gpu"
        elif 'torch' in content or 'pytorch' in content:
            return "pytorch/pytorch:latest"
        else:
            # Default to PyTorch
            return "pytorch/pytorch:latest"
    
    async def wait_for_completion(self, container_id: str):
        """Wait for container to complete and return status"""
        try:
            container = self.client.containers.get(container_id)
            
            # Wait for container to finish (non-blocking with asyncio)
            while True:
                container.reload()
                if container.status == 'exited':
                    break
                await asyncio.sleep(5)
            
            # Get exit code
            exit_code = container.attrs['State']['ExitCode']
            
            if exit_code == 0:
                return {"status": "success"}
            else:
                logs = container.logs().decode('utf-8')
                return {"status": "failed", "error": logs[-1000:]}  # Last 1000 chars
        
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def stop_container(self, container_id: str):
        """Stop a running container"""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=10)
            container.remove()
        except Exception as e:
            Logger.error(f"Error stopping container: {e}")
    
    async def get_container_logs(self, container_id: str, tail: int = 100):
        """Get container logs"""
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=tail).decode('utf-8')
            return logs
        except Exception as e:
            return f"Error getting logs: {e}"