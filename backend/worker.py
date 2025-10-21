import redis
import json
import os
import time
import zipfile
import shutil
from datetime import datetime

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

# Initialize Docker client with proper error handling
docker_client = None

def get_docker_client():
    """Get or create Docker client with error handling"""
    global docker_client
    if docker_client is not None:
        return docker_client
    
    try:
        import docker
        
        print("\nAttempting to connect to Docker...")
        
        # Method 1: Try with explicit socket path (most reliable for Docker Desktop)
        try:
            home = os.path.expanduser("~")
            socket_path = f'{home}/.docker/run/docker.sock'
            if os.path.exists(socket_path):
                print(f"  Trying: unix://{socket_path}...")
                docker_client = docker.DockerClient(base_url=f'unix://{socket_path}')
                docker_client.ping()
                print(f"  ✓ Connected to Docker via {socket_path}")
                return docker_client
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        
        # Method 2: Try /var/run/docker.sock
        try:
            if os.path.exists('/var/run/docker.sock'):
                print("  Trying: unix:///var/run/docker.sock...")
                docker_client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
                docker_client.ping()
                print("  ✓ Connected to Docker via /var/run/docker.sock")
                return docker_client
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        
        # Method 3: Try from_env with explicit environment
        try:
            print("  Trying: docker.from_env()...")
            os.environ['DOCKER_HOST'] = f'unix://{os.path.expanduser("~")}/.docker/run/docker.sock'
            docker_client = docker.from_env()
            docker_client.ping()
            print("  ✓ Connected to Docker via from_env()")
            return docker_client
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        
        print("\n✗ Could not connect to Docker using any method")
        print("\nThis might be a docker-py library issue. Try:")
        print("1. pip uninstall docker docker-py")
        print("2. pip install docker")
        print("3. Or use docker-compose (recommended)")
        return None
        
    except ImportError:
        print("✗ Docker library not installed")
        print("Install with: pip install docker")
        return None
    except Exception as e:
        print(f"✗ Error initializing Docker client: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_job_files(job_id):
    """Extract uploaded zip file"""
    zip_path = f"{UPLOADS_DIR}/{job_id}.zip"
    job_dir = f"{JOBS_DIR}/{job_id}"
    
    os.makedirs(job_dir, exist_ok=True)
    
    print(f"  Extracting {zip_path} to {job_dir}")
    
    if not os.path.exists(zip_path):
        raise Exception(f"Zip file not found: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(job_dir)
    
    # List extracted contents for debugging
    print(f"  Extracted files:")
    for root, dirs, files in os.walk(job_dir):
        level = root.replace(job_dir, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")
    
    return job_dir


def check_resource_available(resource):
    """Check if GPU/CPU resource is available"""
    return not r.exists(f"resource:{resource}")


def acquire_resource(resource, job_id):
    """Acquire a resource (GPU or CPU)"""
    r.set(f"resource:{resource}", job_id)


def release_resource(resource):
    """Release a resource"""
    r.delete(f"resource:{resource}")


def run_training_job(job_id, job_data):
    """Run the training job in Docker"""
    client = get_docker_client()
    
    if client is None:
        job_data["status"] = "failed"
        job_data["error"] = "Docker client not available"
        job_data["completed_at"] = datetime.now().isoformat()
        r.set(f"job:{job_id}", json.dumps(job_data))
        release_resource(job_data["resource"])
        return
    
    try:
        # Get docker image from job data
        docker_image = job_data["docker_image"]
        resource = job_data["resource"]
        
        # Extract files
        job_dir = extract_job_files(job_id)
        output_dir = f"{OUTPUTS_DIR}/{job_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # When running in Docker, we need to use host paths for volume mounts
        host_data_dir = os.getenv('HOST_DATA_DIR')
        
        # Verify files exist before mounting
        print(f"  Checking extracted files in {job_dir}:")
        if os.path.exists(job_dir):
            files = os.listdir(job_dir)
            print(f"  Files: {files}")
            
            # Check for requirements.txt and train.py
            has_req = any('requirements.txt' in f for f in files)
            has_train = any('train.py' in f for f in files)
            print(f"  Has requirements.txt: {has_req}")
            print(f"  Has train.py: {has_train}")
        else:
            print(f"  ERROR: Job directory does not exist!")
        
        if host_data_dir:
            # Running in Docker with HOST_DATA_DIR set
            host_job_dir = f"{host_data_dir}/jobs/{job_id}"
            host_output_dir = f"{host_data_dir}/outputs/{job_id}"
            
            print(f"  Running in Docker - using host paths")
            print(f"  Host job dir: {host_job_dir}")
            print(f"  Host output dir: {host_output_dir}")
            
            # Verify host paths exist (they should be visible via the mount)
            if os.path.exists(host_job_dir):
                print(f"  ✓ Host job dir exists and is accessible")
            else:
                print(f"  ✗ WARNING: Host job dir not accessible from worker")
            
            volumes = {
                host_job_dir: {'bind': '/workspace', 'mode': 'rw'},
                host_output_dir: {'bind': '/output', 'mode': 'rw'}
            }
        else:
            # Running locally - use absolute paths directly
            print(f"  Running locally - using local paths")
            volumes = {
                os.path.abspath(job_dir): {'bind': '/workspace', 'mode': 'rw'},
                os.path.abspath(output_dir): {'bind': '/output', 'mode': 'rw'}
            }
        
        print(f"  Volume mounts: {volumes}")
        
        # Prepare log file
        log_file = f"{job_dir}/output.log"
        
        # Create empty log file
        with open(log_file, 'w') as f:
            f.write(f"Job started at {datetime.now().isoformat()}\n")
            f.write(f"Resource: {resource}\n")
            f.write(f"Docker Image: {docker_image}\n")
            f.write("-" * 50 + "\n\n")
        
        # Update job status
        job_data["status"] = "running"
        job_data["started_at"] = datetime.now().isoformat()
        r.set(f"job:{job_id}", json.dumps(job_data))
        
        print(f"  Extracting files to {job_dir}")
        print(f"  Output directory: {output_dir}")
        print(f"  Log file: {log_file}")
        
        # Prepare Docker run command
        
        # Set up device requests for GPU
        device_requests = None
        runtime = None
        
        if resource.startswith("gpu:"):
            gpu_id = resource.split(":")[1]
            
            # Check if we're running inside Docker (worker in container)
            if os.path.exists("/.dockerenv"):
                # Running in Docker - use nvidia runtime
                runtime = "nvidia"
                # Set GPU device via environment variable
                environment = {
                    'PYTHONUNBUFFERED': '1',
                    'NVIDIA_VISIBLE_DEVICES': gpu_id
                }
            else:
                # Running locally - use device requests
                import docker
                device_requests = [
                    docker.types.DeviceRequest(
                        device_ids=[gpu_id],
                        capabilities=[['gpu']]
                    )
                ]
                environment = {'PYTHONUNBUFFERED': '1'}
        else:
            environment = {'PYTHONUNBUFFERED': '1'}
        
        # Run container
        print(f"  Starting Docker container with image: {docker_image}")
        
        # Build command that handles nested directories
        command = '''bash -c "
            cd /workspace
            echo 'Contents of /workspace:'
            ls -la
            
            # Find requirements.txt and train.py
            REQ_FILE=$(find . -name 'requirements.txt' -type f | head -n 1)
            TRAIN_FILE=$(find . -name 'train.py' -type f | head -n 1)
            
            if [ -z '$REQ_FILE' ]; then
                echo 'ERROR: requirements.txt not found'
                exit 1
            fi
            
            if [ -z '$TRAIN_FILE' ]; then
                echo 'ERROR: train.py not found'
                exit 1
            fi
            
            echo 'Found requirements.txt at:' $REQ_FILE
            echo 'Found train.py at:' $TRAIN_FILE
            
            # Change to directory containing train.py
            TRAIN_DIR=$(dirname $TRAIN_FILE)
            cd $TRAIN_DIR
            echo 'Changed to directory:' $(pwd)
            
            # Install requirements
            pip install -r requirements.txt
            
            # Run training
            python train.py
        "'''
        
        container_kwargs = {
            'image': docker_image,
            # 'command': 'bash -c "cd /workspace && pip install -r requirements.txt && python train.py"',
            'command': command,
            'volumes': volumes,
            'detach': True,
            'stdout': True,
            'stderr': True,
            'remove': False,
            'environment': environment,
            'name': f"ml-job-{job_id}"
        }
        
        if device_requests:
            container_kwargs['device_requests'] = device_requests
        
        if runtime:
            container_kwargs['runtime'] = runtime
        
        container = client.containers.run(**container_kwargs)
        
        # Store container ID in Redis for cancellation
        r.set(f"container:{job_id}", container.id)
        
        print(f"  Container started: {container.id[:12]}")
        print(f"  Streaming logs to {log_file}")
        
        # Stream logs to file in real-time
        with open(log_file, 'ab') as f:
            for log_chunk in container.logs(stream=True, follow=True, stdout=True, stderr=True):
                f.write(log_chunk)
                f.flush()
                # Also print to console for debugging
                try:
                    print(log_chunk.decode('utf-8'), end='')
                except:
                    pass
        
        # Wait for container to finish
        result = container.wait()
        
        print(f"  Container finished with exit code: {result['StatusCode']}")
        
        # Check if job was cancelled before updating status
        # Reload job data from Redis to get the latest status
        current_job_data = r.get(f"job:{job_id}")
        if current_job_data:
            current_job = json.loads(current_job_data)
            if current_job["status"] == "cancelled":
                print(f"  Job was cancelled, preserving cancelled status")
                job_data = current_job  # Use the current status from Redis
                # Clean up container
                try:
                    container.remove()
                    print(f"  Container removed")
                except:
                    pass
                return  # Exit early, don't update status
        
        # Check exit code
        # Exit code 137 typically means SIGKILL (often from cancellation)
        # if result['StatusCode'] == 137:
        #     # Double-check if this was a cancellation
        #     current_job_data = r.get(f"job:{job_id}")
        #     if current_job_data:
        #         current_job = json.loads(current_job_data)
        #         if current_job["status"] == "cancelled":
        #             print(f"  Job was cancelled (exit code 137)")
        #             job_data = current_job
        #             try:
        #                 container.remove()
        #                 print(f"  Container removed")
        #             except:
        #                 pass
        #             return
        
        if result['StatusCode'] == 0:
            job_data["status"] = "completed"
            print(f"  ✓ Job completed successfully")
        else:
            job_data["status"] = "failed"
            job_data["error"] = f"Container exited with code {result['StatusCode']}"
            print(f"  ✗ Job failed with exit code {result['StatusCode']}")
        
        # Clean up container
        container.remove()
        print(f"  Container removed")
        
    except Exception as e:
        # Check if job was cancelled before marking as failed
        current_job_data = r.get(f"job:{job_id}")
        if current_job_data:
            current_job = json.loads(current_job_data)
            if current_job["status"] == "cancelled":
                print(f"  Job was cancelled, not marking as failed")
                job_data = current_job
                return
        
        job_data["status"] = "failed"
        job_data["error"] = str(e)
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Write error to log
        log_file = f"{JOBS_DIR}/{job_id}/output.log"
        try:
            with open(log_file, 'a') as f:
                f.write(f"\n\n{'='*50}\n")
                f.write(f"ERROR: {str(e)}\n")
                f.write(f"{'='*50}\n")
                traceback.print_exc(file=f)
        except:
            pass
    
    finally:
        # Update final status - but only if not cancelled
        current_job_data = r.get(f"job:{job_id}")
        if current_job_data:
            current_job = json.loads(current_job_data)
            if current_job["status"] != "cancelled":
                job_data["completed_at"] = datetime.now().isoformat()
                r.set(f"job:{job_id}", json.dumps(job_data))
        
        # Release resource
        release_resource(job_data["resource"])


def process_pending_jobs():
    """Main worker loop to process pending jobs"""
    print("Worker started. Polling for jobs...")
    
    # Initialize Docker client on startup
    client = get_docker_client()
    if client is None:
        print("\n⚠️  WARNING: Worker started but Docker is not available!")
        print("Jobs will fail until Docker connection is established.\n")
    
    while True:
        try:
            # Get pending job
            job_id = r.rpop("queue:pending")
            
            if job_id:
                # Get job data
                job_data = json.loads(r.get(f"job:{job_id}"))
                
                # Check if job was cancelled
                if job_data["status"] == "cancelled":
                    continue
                
                resource = job_data["resource"]
                
                # Check if resource is available
                if check_resource_available(resource):
                    print(f"Starting job {job_id} on {resource}")
                    
                    # Acquire resource
                    acquire_resource(resource, job_id)
                    
                    # Run job
                    run_training_job(job_id, job_data)
                    
                    print(f"Job {job_id} completed")
                else:
                    # Resource not available, put job back in queue
                    r.rpush("queue:pending", job_id)
                    time.sleep(2)
            else:
                # No pending jobs, wait
                time.sleep(5)
                
        except Exception as e:
            print(f"Worker error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    process_pending_jobs()