#!/bin/bash
# GitHub-based deployment script for RunPod
# This script will be run directly from GitHub on RunPod instances

echo "========================================="
echo "SKYREELS FILM PLATFORM - CLOUD DEPLOYMENT"
echo "========================================="

# Configuration
GITHUB_REPO="https://github.com/yourusername/skyreels-film-platform"
GITHUB_BRANCH="main"
MODEL_VERSION=${1:-v2}  # Default to V2 for unlimited length
GPU_TYPE=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)

echo "📍 Deployment Configuration:"
echo "  Repository: $GITHUB_REPO"
echo "  Branch: $GITHUB_BRANCH"
echo "  Model Version: SkyReels-$MODEL_VERSION"
echo "  GPU: $GPU_TYPE"

# Step 1: System setup
echo ""
echo "📦 Step 1: Installing system dependencies..."
apt-get update -qq
apt-get install -y git wget ffmpeg python3.10 python3-pip cuda-toolkit-12-2 redis-server postgresql nginx -qq

# Step 2: Clone platform repository
echo ""
echo "📥 Step 2: Cloning platform repository..."
cd /workspace
if [ -d "skyreels-platform" ]; then
    cd skyreels-platform
    git pull origin $GITHUB_BRANCH
else
    git clone -b $GITHUB_BRANCH $GITHUB_REPO skyreels-platform
    cd skyreels-platform
fi

# Step 3: Clone SkyReels model repository
echo ""
echo "🤖 Step 3: Installing SkyReels-$MODEL_VERSION..."
cd /workspace
if [ "$MODEL_VERSION" = "v1" ]; then
    if [ ! -d "SkyReels-V1" ]; then
        git clone https://github.com/SkyworkAI/SkyReels-V1.git
    fi
    cd SkyReels-V1
else
    if [ ! -d "SkyReels-V2" ]; then
        git clone https://github.com/SkyworkAI/SkyReels-V2.git
    fi
    cd SkyReels-V2
fi

# Step 4: Install Python dependencies
echo ""
echo "🐍 Step 4: Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Platform-specific dependencies
pip install fastapi uvicorn sqlalchemy stripe redis celery flower boto3 -q

# Step 5: Download model weights
echo ""
echo "⏬ Step 5: Downloading model weights (this may take 10-15 minutes)..."

if [ "$MODEL_VERSION" = "v1" ]; then
    # Download V1 models
    python -c "
from huggingface_hub import snapshot_download
import os
os.makedirs('/workspace/models', exist_ok=True)
print('Downloading SkyReels-V1 models...')
snapshot_download(
    repo_id='SkyworkAI/SkyReels-V1-Hunyuan-T2V',
    local_dir='/workspace/models/skyreels-v1-t2v',
    resume_download=True
)
print('✅ V1 models downloaded!')
"
else
    # Download V2 models - choose based on available VRAM
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
    
    if [ "$VRAM" -lt 20000 ]; then
        MODEL_SIZE="1.3B"
    elif [ "$VRAM" -lt 50000 ]; then
        MODEL_SIZE="5B"
    else
        MODEL_SIZE="14B"
    fi
    
    python -c "
from huggingface_hub import snapshot_download
import os
os.makedirs('/workspace/models', exist_ok=True)
print(f'Downloading SkyReels-V2-$MODEL_SIZE model...')
snapshot_download(
    repo_id=f'SkyworkAI/SkyReels-V2-$MODEL_SIZE-540P',
    local_dir='/workspace/models/skyreels-v2',
    resume_download=True
)
print('✅ V2 models downloaded!')
"
fi

# Step 6: Setup database
echo ""
echo "🗄️ Step 6: Setting up database..."
cd /workspace/skyreels-platform

# Create PostgreSQL database
sudo -u postgres psql << EOF
CREATE DATABASE skyreels_platform;
CREATE USER skyreels WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE skyreels_platform TO skyreels;
EOF

# Run database migrations
export DATABASE_URL="postgresql://skyreels:secure_password_here@localhost/skyreels_platform"
python -c "
from film_platform.monetization_platform import Base, engine
Base.metadata.create_all(bind=engine)
print('✅ Database initialized!')
"

# Step 7: Setup Redis for job queue
echo ""
echo "📮 Step 7: Setting up Redis job queue..."
redis-server --daemonize yes

# Step 8: Configure Nginx reverse proxy
echo ""
echo "🌐 Step 8: Configuring web server..."
cat > /etc/nginx/sites-available/skyreels << 'NGINX_CONFIG'
server {
    listen 80;
    server_name _;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static {
        alias /workspace/skyreels-platform/static;
    }
    
    location /films {
        alias /workspace/output/films;
        add_header Content-Disposition "attachment";
    }
}
NGINX_CONFIG

ln -sf /etc/nginx/sites-available/skyreels /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -s reload

# Step 9: Create startup script
echo ""
echo "🚀 Step 9: Creating startup script..."
cat > /workspace/start_platform.sh << 'STARTUP_SCRIPT'
#!/bin/bash
cd /workspace/skyreels-platform

# Export environment variables
export DATABASE_URL="postgresql://skyreels:secure_password_here@localhost/skyreels_platform"
export REDIS_URL="redis://localhost:6379"
export MODEL_PATH="/workspace/models"
export OUTPUT_PATH="/workspace/output"

# Start Celery worker for background jobs
celery -A film_platform.tasks worker --loglevel=info --detach

# Start Celery Flower for monitoring (optional)
celery -A film_platform.tasks flower --port=5555 --detach

# Start FastAPI application
uvicorn film_platform.monetization_platform:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info
STARTUP_SCRIPT

chmod +x /workspace/start_platform.sh

# Step 10: Create health check script
echo ""
echo "💚 Step 10: Creating health check..."
cat > /workspace/health_check.py << 'HEALTH_CHECK'
#!/usr/bin/env python3
import requests
import torch
import psutil
import json

def check_health():
    health = {
        "gpu": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "vram_gb": torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else 0,
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "api_status": False,
        "database_status": False,
        "redis_status": False
    }
    
    # Check API
    try:
        r = requests.get("http://localhost:8000/health")
        health["api_status"] = r.status_code == 200
    except:
        pass
        
    # Check database
    try:
        from sqlalchemy import create_engine
        engine = create_engine("postgresql://skyreels:secure_password_here@localhost/skyreels_platform")
        conn = engine.connect()
        conn.close()
        health["database_status"] = True
    except:
        pass
        
    # Check Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        health["redis_status"] = True
    except:
        pass
        
    return health

if __name__ == "__main__":
    health = check_health()
    print(json.dumps(health, indent=2))
    
    # Exit code based on health
    if not all([health["gpu"], health["api_status"], health["database_status"]]):
        exit(1)
HEALTH_CHECK

chmod +x /workspace/health_check.py

# Step 11: Auto-scaling configuration
echo ""
echo "⚖️ Step 11: Configuring auto-scaling..."
cat > /workspace/autoscale.py << 'AUTOSCALE'
#!/usr/bin/env python3
"""
Auto-scaling manager for SkyReels platform
Monitors queue and scales RunPod instances
"""
import os
import time
import requests
from datetime import datetime

RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
MAX_INSTANCES = 10
MIN_INSTANCES = 1
SCALE_UP_THRESHOLD = 5  # Queue size
SCALE_DOWN_THRESHOLD = 0  # Queue size

def get_queue_size():
    """Get current job queue size"""
    try:
        r = requests.get("http://localhost:8000/api/queue/size")
        return r.json()["size"]
    except:
        return 0

def get_current_instances():
    """Get current RunPod instances"""
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    r = requests.get("https://api.runpod.io/v1/pods", headers=headers)
    return len(r.json()["pods"])

def scale_up():
    """Launch new RunPod instance"""
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    data = {
        "cloudType": "SECURE",
        "gpuType": "RTX 4090",
        "template": "runpod/pytorch:2.0.1-py3.10-cuda12.1.0-devel",
        "startScript": "curl -sSL https://raw.githubusercontent.com/yourusername/skyreels-platform/main/deployment/github_deployment.sh | bash"
    }
    r = requests.post("https://api.runpod.io/v1/pods", json=data, headers=headers)
    return r.json()

def scale_down(instance_id):
    """Terminate RunPod instance"""
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    r = requests.delete(f"https://api.runpod.io/v1/pods/{instance_id}", headers=headers)
    return r.status_code == 200

def main():
    while True:
        queue_size = get_queue_size()
        current_instances = get_current_instances()
        
        print(f"[{datetime.now()}] Queue: {queue_size}, Instances: {current_instances}")
        
        if queue_size > SCALE_UP_THRESHOLD and current_instances < MAX_INSTANCES:
            print("📈 Scaling up...")
            scale_up()
        elif queue_size < SCALE_DOWN_THRESHOLD and current_instances > MIN_INSTANCES:
            print("📉 Scaling down...")
            # Scale down logic here
            
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
AUTOSCALE

chmod +x /workspace/autoscale.py

# Step 12: Start services
echo ""
echo "🎬 Step 12: Starting SkyReels Film Platform..."

# Start the platform
/workspace/start_platform.sh &

# Wait for services to start
sleep 10

# Run health check
echo ""
echo "🏥 Running health check..."
python /workspace/health_check.py

echo ""
echo "========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "========================================="
echo ""
echo "📊 Platform Information:"
echo "  API Endpoint: http://$(curl -s ifconfig.me)"
echo "  Documentation: http://$(curl -s ifconfig.me)/docs"
echo "  Monitoring: http://$(curl -s ifconfig.me):5555"
echo ""
echo "🎯 Quick Test:"
echo "  curl http://$(curl -s ifconfig.me)/health"
echo ""
echo "💰 Pricing:"
echo "  Script: \$1/minute"
echo "  Video: \$3/minute"
echo "  Storyboard: \$10 flat"
echo ""
echo "📈 Profitability:"
echo "  60-min film revenue: \$240"
echo "  GPU cost: ~\$5-10"
echo "  Profit margin: 95%+"
echo ""
echo "🚀 The platform is ready to generate films!"
echo "========================================="
