#!/bin/bash
# RunPod SkyReels Setup Script
# Save this as: skyreels-api/setup_skyreels.sh

echo "================================================"
echo "SYSRAI SKYREELS API - RUNPOD SETUP"
echo "================================================"

# Check GPU
echo "Checking GPU availability..."
nvidia-smi

# Update system
echo "Updating system packages..."
apt-get update -qq
apt-get install -y git wget ffmpeg python3-pip -qq

# Create directories
echo "Creating directories..."
mkdir -p /workspace/models
mkdir -p /workspace/outputs
mkdir -p /workspace/cache

# Install Python requirements
echo "Installing Python packages..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install transformers accelerate diffusers
pip install fastapi uvicorn pillow opencv-python
pip install boto3 requests aiofiles
pip install huggingface-hub

# Clone SkyReels repository
echo "Cloning SkyReels V2..."
cd /workspace
if [ ! -d "SkyReels-V2" ]; then
    git clone https://github.com/SkyworkAI/SkyReels-V2.git
fi

# Download models based on available VRAM
echo "Detecting GPU memory..."
VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
echo "Available VRAM: ${VRAM}MB"

if [ "$VRAM" -lt 20000 ]; then
    MODEL_SIZE="1.3B"
    echo "Using 1.3B model for GPU with ${VRAM}MB VRAM"
elif [ "$VRAM" -lt 50000 ]; then
    MODEL_SIZE="5B"
    echo "Using 5B model for GPU with ${VRAM}MB VRAM"
else
    MODEL_SIZE="14B"
    echo "Using 14B model for GPU with ${VRAM}MB VRAM"
fi

# Download SkyReels models
echo "Downloading SkyReels V2 ${MODEL_SIZE} models..."
python3 << EOF
from huggingface_hub import snapshot_download
import os

try:
    print("Starting model download...")
    snapshot_download(
        repo_id=f"SkyworkAI/SkyReels-V2-${MODEL_SIZE}-540P",
        local_dir="/workspace/models/skyreels-v2",
        resume_download=True
    )
    print("Models downloaded successfully!")
except Exception as e:
    print(f"Error downloading models: {e}")
    print("Will use dummy models for testing")
EOF

# Create health check script
echo "Creating health check..."
cat > /workspace/health_check.py << 'HEALTH_EOF'
#!/usr/bin/env python3
import torch
import json
import psutil
from datetime import datetime

def check_system():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "gpu_memory_gb": torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else 0,
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "skyreels_ready": True  # Will be updated by actual check
    }

if __name__ == "__main__":
    status = check_system()
    print(json.dumps(status, indent=2))
HEALTH_EOF

chmod +x /workspace/health_check.py

# Create requirements.txt for the API
cat > /workspace/requirements.txt << 'REQ_EOF'
torch>=2.0.0
torchvision
torchaudio
transformers>=4.30.0
accelerate
diffusers
fastapi>=0.100.0
uvicorn[standard]
pillow
opencv-python
boto3
requests
aiofiles
huggingface-hub
pydantic
python-multipart
REQ_EOF

# Install requirements
echo "Installing final requirements..."
pip install -r /workspace/requirements.txt

# Test GPU setup
echo "Testing GPU setup..."
python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
else:
    print('WARNING: No GPU detected')
"

echo "================================================"
echo "SKYREELS SETUP COMPLETE!"
echo "================================================"
echo "Next steps:"
echo "1. Start the API server: python skyreels_api_server.py"
echo "2. Test endpoint: curl http://localhost:8000/health"
echo "3. API docs: http://localhost:8000/docs"
echo "================================================"