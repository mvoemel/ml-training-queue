# ML Training Job Queue System

A simple web application for managing and queuing machine learning training jobs on GPU/CPU resources.

**Disclaimer**: In this application authentication and input validation is not implemented. Thus you should never use it in a production environment as it is not save to run it exposed to third party users. The Docker socket is mounted, thus be cautious about what training scripts you run.

## Features

- Upload training jobs as ZIP files containing `dataset`, `train.py`, and `requirements.txt`
- Select GPU or CPU for training
- Choose Docker image (`pytorch/pytorch:latest`, `tensorflow/tensorflow:latest`, etc.)
- Automatic job queue management
- Real-time console output streaming
- Download trained models (contains everything in the `/output/` directory of set job)
- Cancel `pending` or `running` jobs
- GPU monitoring and utilization tracking
- Parallel job execution on different resources (CPU, GPU 0, GPU 1, etc.)

## Project Structure

```
project/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py          # FastAPI backend
│   └── worker.py        # Job processor
├── examples/            # Example training datasets and scripts
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── components/
│       ├── main.jsx
│       ├── App.jsx       # Dashboard
│       ├── JobDetail.jsx # Job detail view
│       └── index.css
└── data/
    ├── uploads/         # Uploaded ZIP files
    ├── jobs/            # Extracted job files
    └── outputs/         # Trained models
```

## Prerequisites

- Docker v28
- NVIDIA GPU with drivers installed
- NVIDIA Container Toolkit for Docker

### Install NVIDIA Container Toolkit

Install the NVIDIA Container Toolkit (enables GPU passthrough to containers):

```bash
# For Ubuntu
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
```

Then configure it:

```bash
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker
```

After this, test:

```bash
# you need propably define the runtime because it propably is not the default
docker run --rm --runtime=nvidia --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

## Setup

1. Clone the repository and create the directory structure:

```bash
mkdir -p data/uploads data/jobs data/outputs
```

2. Create a `.env` file containing the path to the directory of this repository:

```bash
nano .env
```

```env
PWD=/path/to/this/repository
```

3. Build and start the services:

```bash
docker compose up --build -d
```

4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

## Preparing a Training Job

Create a ZIP file with the following structure:

```
your_model.zip
├── dataset/              # Your training data
│   ├── train/
│   ├── test/
│   ├── val/
│   └── ...
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

## Available Docker Images

The system comes pre-configured with:

- `pytorch/pytorch:latest`
- `pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime`
- `tensorflow/tensorflow:latest-gpu`
- `tensorflow/tensorflow:latest`

You can add more images by modifying the `dockerImages` array in `frontend/src/App.jsx`.

## Development

**Prerequisites for local development:**

- Python 3.11+
- Node.js 18+
- Redis running locally
- Docker daemon running (for worker to launch training containers)

**1. Create data directories:**

```bash
mkdir -p data/uploads data/jobs data/outputs
```

**2. Create `.env` file with:**

```env
PWD=.
```

**3. Start Redis:**

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

**4. Setup Backend:**

```bash
cd backend

# Create virtual environment (e.g. using conda)
conda activate <your_env>

# Install dependencies
pip install -r requirements.txt
```

**5. Setup Frontend:**

```bash
cd frontend
npm install
```

**6. Start services in separate terminals:**

**Terminal 1 - Backend API:**

```bash
cd backend
conda activate <your_env>
uvicorn main:app --reload
```

**Terminal 2 - Worker:**

```bash
cd backend
conda activate <your_env>
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

## Troubleshooting

```bash
# Get logs of a specific container
docker logs mltq-worker-1
```

### `OSError: [Errno 28] No space left on device`

```bash
# Clean up old images, etc.
docker system prune -a
```

## Delete all data

```bash
# Step 1: Stop the containers
docker compose down

# Step 2: Remove the redis volume (e.g. "mltq_redis_data"), if it does not work check the name first
# docker volume ls
docker volume rm mltq_redis_data

# Step 3: Delete the data directories and all its content
rm -r data

# Step 4: Init the empty data directories
mkdir -p data/uploads data/jobs data/outputs
```

## License

MIT
