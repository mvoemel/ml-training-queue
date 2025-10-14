# ML Training Job Queue System

A simple web application for managing and queuing machine learning training jobs on GPU/CPU resources.

**Disclaimer**: In this application authentication and input validation is not implemented. Thus you should never use it in a production environment as it is not save to run it exposed to third party users.

## Features

- Upload training jobs as ZIP files containing dataset, train.py, and requirements.txt
- Select GPU or CPU for training
- Choose Docker image (PyTorch, TensorFlow, etc.)
- Automatic job queue management
- Real-time console output streaming
- Download trained models
- GPU monitoring and utilization tracking
- Parallel job execution on different resources

## Project Structure

```
project/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py          # FastAPI backend
│   └── worker.py        # Job processor
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx      # Dashboard
│       ├── JobDetail.jsx # Job detail view
│       └── index.css
└── data/
    ├── uploads/         # Uploaded ZIP files
    ├── jobs/            # Extracted job files
    └── outputs/         # Trained models
```

## Prerequisites

- Docker and Docker Compose
- NVIDIA GPU with drivers installed (optional, for GPU training)
- NVIDIA Container Toolkit for Docker

### Install NVIDIA Container Toolkit

```bash
# Add the package repositories
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Install nvidia-docker2
sudo apt-get update
sudo apt-get install -y nvidia-docker2

# Restart Docker daemon
sudo systemctl restart docker
```

## Setup

1. Clone the repository and create the directory structure:

```bash
mkdir -p data/uploads data/jobs data/outputs
```

2. Build and start the services:

```bash
docker-compose up --build
```

3. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

## Usage

### Preparing Your Training Job

Create a ZIP file with the following structure:

```
your_model.zip
├── dataset/              # Your training data
│   ├── train/
│   ├── test/
│   └── val/
├── train.py              # Training script
└── requirements.txt      # Python dependencies
```

**Important: Your `train.py` script should:**

- Read data from `./dataset/`
- Save trained models/outputs to `/output/`
- Use standard print statements for logging (they'll appear in real-time)

Example `train.py`:

```python
import torch
import os

# Read data from ./dataset/
train_data = load_data('./dataset/train/')

# Train your model
model = YourModel()
model.train()

# Save output to /output/
os.makedirs('/output', exist_ok=True)
torch.save(model.state_dict(), '/output/model.pth')
print("Training completed!")
```

### Creating a Job

1. Open the web interface at http://localhost:3000
2. Upload your ZIP file
3. Select the resource (CPU or GPU)
4. Select the Docker image
5. Click "Create Job"

### Monitoring Jobs

- **Dashboard**: View all jobs with their status
- **Job Details**: Click on any job to see:
  - Job information and metadata
  - GPU utilization (if using GPU)
  - Real-time console output
  - Download button for completed jobs

### Cancelling Jobs

- Click the "Cancel" button on pending or running jobs
- The job will be marked as cancelled and resources will be released

### Downloading Results

- Once a job is completed, click the "Download" button
- You'll receive a ZIP file containing everything in the `/output/` directory

## Available Docker Images

The system comes pre-configured with:

- `pytorch/pytorch:latest`
- `pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime`
- `tensorflow/tensorflow:latest-gpu`
- `tensorflow/tensorflow:latest`

You can add more images by modifying the `dockerImages` array in `frontend/src/App.jsx`.

## Resource Management

- The system tracks which resources (GPUs/CPU) are in use
- Jobs assigned to different resources run in parallel
- When a resource becomes available, the next pending job for that resource starts automatically
- Example: GPU 0 and GPU 1 can each run one job simultaneously

## Development

### Running Locally (without Docker)

**Prerequisites for local development:**

- Python 3.11+
- Node.js 18+
- Redis running locally
- Docker daemon running (for worker to launch training containers)

**1. Create data directories:**

```bash
mkdir -p data/uploads data/jobs data/outputs
```

**2. Start Redis:**

```bash
# macOS with Homebrew
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Or use Docker for Redis only
docker run -d -p 6379:6379 redis:7-alpine

# Verify Redis is running
redis-cli ping  # Should return "PONG"
```

**3. Setup Backend:**

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
# or use conda
conda activate <your_env>

# Install dependencies
pip install -r requirements.txt
```

**4. Setup Frontend:**

```bash
cd frontend
npm install
```

**5. Start services in separate terminals:**

**Terminal 1 - Backend API:**

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

**Terminal 2 - Worker:**

```bash
cd backend
source venv/bin/activate
python worker.py
```

**Terminal 3 - Frontend:**

```bash
cd frontend
npm run dev
```

**Access at:**

- Frontend: http://localhost:5173 (Vite dev server)
- Backend API: http://localhost:8000

**Troubleshooting Docker connection on macOS:**

If the worker can't connect to Docker, try these solutions in order:

1. **Make sure Docker Desktop is running:**

   ```bash
   docker ps  # Should show running containers or empty list, not an error
   ```

2. **Set DOCKER_HOST environment variable:**

   ```bash
   # For Docker Desktop on macOS
   export DOCKER_HOST=unix://$HOME/.docker/run/docker.sock

   # Then run the worker
   python worker.py
   ```

3. **Grant permissions to Docker socket:**

   ```bash
   # If using /var/run/docker.sock
   sudo chmod 666 /var/run/docker.sock
   ```

4. **Best option - Use docker-compose:**

   Docker-compose handles all the connection issues automatically:

   ```bash
   docker-compose up --build
   ```

   This is the recommended approach as it avoids all local Docker connection issues.

### Environment Variables

- `REDIS_URL`: Redis connection URL (default: `redis://redis:6379`)

## Troubleshooting

### GPU not detected

- Ensure NVIDIA drivers are installed: `nvidia-smi`
- Verify Docker can access GPU: `docker run --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi`
- Check NVIDIA Container Toolkit is installed

### Jobs stuck in pending

- Check worker logs: `docker-compose logs worker`
- Ensure Docker socket is mounted correctly
- Verify Redis is running: `docker-compose logs redis`

### Training script errors

- Check job logs in the web interface
- Ensure your `train.py` reads from `./dataset/` and writes to `/output/`
- Verify all dependencies are in `requirements.txt`

## Scaling

To run multiple workers for faster processing:

```bash
docker-compose up --scale worker=3
```

## Security Notes

- This application has **no authentication** - suitable for local/trusted networks only
- For production use, add authentication and HTTPS
- The Docker socket is mounted - be cautious about what training scripts you run

## License

MIT
