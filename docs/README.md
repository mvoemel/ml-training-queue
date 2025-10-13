# ML Training Queue System

A web-based system for managing and queuing deep learning training jobs on GPU servers.

## Features

- **User Management**: First user registration, then admin can create/delete users
- **Job Queue**: Submit training jobs with dataset, script, and requirements
- **GPU Management**: Assign jobs to specific GPUs, track utilization
- **Real-time Monitoring**: Live logs and GPU stats during training
- **Parallel Execution**: Run multiple jobs simultaneously on different GPUs
- **Dockerized Training**: Isolated training environments for each job
- **Large File Upload**: Efficient chunked uploads for datasets up to 5GB
- **Model Download**: Download trained models after completion

## Architecture

- **Frontend**: React + TypeScript + Vite
- **Backend**: FastAPI + SQLAlchemy + Redis
- **Queue System**: Redis-based job queue with GPU scheduling
- **Training**: Docker containers with GPU support
- **Database**: SQLite for metadata

## Prerequisites

- Docker and Docker Compose
- NVIDIA Docker runtime (for GPU support)
- NVIDIA drivers installed on host

## Project Structure

```
.
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── models.py
│       ├── schemas.py
│       ├── database.py
│       ├── auth.py
│       ├── services/
│       │   ├── job_scheduler.py
│       │   ├── docker_runner.py
│       │   └── gpu_monitor.py
│       └── workers/
│           └── training_worker.py
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── services/
│       │   └── api.ts
│       └── components/
│           ├── Login.tsx
│           ├── Dashboard.tsx
│           ├── JobForm.tsx
│           ├── JobDetails.tsx
│           └── UserManagement.tsx
└── data/
    ├── app.db (created automatically)
    ├── uploads/
    ├── jobs/
    └── outputs/
```

## Setup Instructions

### 1. Install NVIDIA Docker Runtime

```bash
# Install NVIDIA Docker
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### 2. Clone and Build

```bash
# Create project directories with proper permissions
mkdir -p data/uploads data/jobs data/outputs
chmod -R 777 data  # Ensure write access for Docker containers

# Build and start services
docker-compose up --build -d

# Check logs to verify everything started
docker-compose logs -f backend
```

### 3. Access the Application

Open your browser and navigate to:

```
http://localhost:3000
```

The first user to register will be the admin.

## Usage

### 1. Register/Login

- First time: Register a new account (only possible if no users exist)
- Subsequent logins: Use your credentials

### 2. Create a Training Job

1. Click "New Job"
2. Fill in job details:
   - Job name
   - Select GPU (0, 1, etc.)
   - Number of CPU cores
3. Upload files:
   - **Dataset**: ZIP file containing your training data
   - **Script**: Python file (train.py) that trains your model
   - **Requirements**: requirements.txt with dependencies

**Important**: Your Python script should:

- Save model outputs to `/workspace/output/` directory
- Use relative path `./dataset/` to access your data
- Example structure:

```python
import torch
# Load data from ./dataset/
# Train model
# Save to /workspace/output/model.pth
torch.save(model.state_dict(), '/workspace/output/model.pth')
```

### 3. Monitor Jobs

- View all jobs in the dashboard
- Click on a job to see:
  - Real-time training logs
  - GPU utilization and memory usage
  - Temperature
  - Job status

### 4. Download Results

Once a job completes:

1. Click "Download" on the job
2. Extract the ZIP file to get your trained model

### 5. Manage Users

Click "Manage Users" to:

- View all users
- Create new users
- Delete users (except yourself)

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register first user
- `POST /api/auth/login` - Login
- `GET /api/auth/check` - Check if registration is available

### Jobs

- `GET /api/jobs` - List all jobs
- `GET /api/jobs/{id}` - Get job details
- `POST /api/jobs` - Create new job (multipart/form-data)
- `DELETE /api/jobs/{id}` - Cancel job
- `GET /api/jobs/{id}/logs` - Get training logs
- `GET /api/jobs/{id}/download` - Download output

### GPUs

- `GET /api/gpus` - List available GPUs
- `GET /api/gpus/{id}/stats` - Get GPU statistics

### Users

- `GET /api/users` - List all users
- `POST /api/users` - Create new user
- `DELETE /api/users/{id}` - Delete user

### WebSocket

- `WS /ws/jobs/{id}` - Real-time job updates

## Configuration

### Environment Variables

Edit `docker-compose.yml` to change:

- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection string
- Upload size limits in nginx.conf

### GPU Configuration

The system automatically detects available GPUs using `nvidia-smi`.

To add more GPUs, they will be automatically detected on next restart.

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Troubleshooting

### GPU Not Detected

```bash
# Check NVIDIA drivers
nvidia-smi

# Check Docker can access GPU
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

### Large Upload Fails

- Check `client_max_body_size` in `frontend/nginx.conf`
- Increase if needed for larger datasets

### Container Build Fails

- Ensure Docker has internet access to pull base images
- Check if PyTorch/TensorFlow images are accessible

### Job Stuck in Pending

- Check worker logs: `docker-compose logs worker`
- Check Redis connection: `docker-compose logs redis`
- Verify GPU availability

## Security Notes

- Change `SECRET_KEY` in `backend/app/auth.py` for production
- Use HTTPS in production
- Implement proper user roles if needed
- Consider adding rate limiting
- Validate uploaded files thoroughly

## License

MIT
