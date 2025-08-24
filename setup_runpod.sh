#!/bin/bash
# RunPod Setup Script for SkyReels API Server
# Run this script on your RunPod GPU instance

echo "========================================="
echo "SKYREELS API SERVER - RUNPOD SETUP"
echo "========================================="

# Check GPU
echo "🔍 Checking GPU availability..."
nvidia-smi
echo ""

# Update system
apt-get update -qq

# Install system dependencies
apt-get install -y git wget ffmpeg python3-pip -qq

# Create workspace directory
mkdir -p /workspace/output
mkdir -p /workspace/models
cd /workspace

# Clone SkyReels repository
echo "📥 Downloading SkyReels V2..."
if [ ! -d "SkyReels-V2" ]; then
    git clone https://github.com/SkyworkAI/SkyReels-V2.git
fi

# Install Python dependencies
cd SkyReels-V2
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Install additional dependencies for API server
pip install fastapi uvicorn python-multipart opencv-python-headless -q

# Download the API server script
echo "📥 Downloading API server..."
cd /workspace
wget -q https://raw.githubusercontent.com/ashnehmet/Sysrai-platform/main/skyreels_server.py

# Download SkyReels models
echo "🤖 Downloading SkyReels models (this may take 15-20 minutes)..."
python3 -c "
import os
from pathlib import Path
from huggingface_hub import snapshot_download

# Create model directory
model_dir = '/workspace/models/skyreels-v2'
Path(model_dir).mkdir(parents=True, exist_ok=True)

print('📦 Downloading SkyReels V2 models...')

# Check available VRAM
import subprocess
try:
    result = subprocess.run(['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'], 
                          capture_output=True, text=True)
    vram_mb = int(result.stdout.strip())
    print(f'Available VRAM: {vram_mb} MB')
    
    # Choose model size based on VRAM
    if vram_mb < 16000:  # < 16GB
        model_repo = 'SkyworkAI/SkyReels-V2-1.3B-540P'
        print('Using 1.3B model for lower VRAM')
    else:  # >= 16GB
        model_repo = 'SkyworkAI/SkyReels-V2-5B-540P'
        print('Using 5B model for better quality')
        
except:
    model_repo = 'SkyworkAI/SkyReels-V2-1.3B-540P'
    print('Defaulting to 1.3B model')

# Download models
snapshot_download(
    repo_id=model_repo,
    local_dir=model_dir,
    resume_download=True
)

print('✅ Models downloaded successfully!')
"

# Create startup script
cat > /workspace/start_api.sh << 'API_SCRIPT'
#!/bin/bash
cd /workspace
echo "🚀 Starting SkyReels API Server..."
echo "📊 GPU Info:"
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader

# Start the API server
python3 skyreels_server.py
API_SCRIPT

chmod +x /workspace/start_api.sh

# Create health check script
cat > /workspace/health_check.py << 'HEALTH_SCRIPT'
#!/usr/bin/env python3
import requests
import json
import sys

def check_health():
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ SkyReels API Server is healthy!")
            print(f"   GPU Available: {data['gpu_available']}")
            print(f"   Model Loaded: {data['model_loaded']}")
            if data['gpu_name']:
                print(f"   GPU: {data['gpu_name']}")
                print(f"   VRAM: {data['vram_gb']:.1f} GB")
            return True
        else:
            print(f"❌ Health check failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    if check_health():
        sys.exit(0)
    else:
        sys.exit(1)
HEALTH_SCRIPT

chmod +x /workspace/health_check.py

# Create test script
cat > /workspace/test_generation.py << 'TEST_SCRIPT'
#!/usr/bin/env python3
import requests
import json
import time

def test_video_generation():
    print("🧪 Testing video generation...")
    
    payload = {
        "prompt": "A person walking through a beautiful garden, cinematic lighting",
        "duration": 5,
        "resolution": "540p",
        "fps": 24
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/generate",
            json=payload,
            timeout=300  # 5 minutes
        )
        
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                print(f"✅ Test generation successful!")
                print(f"   Generation time: {result['generation_time']:.1f}s")
                print(f"   Video URL: {result['video_url']}")
                return True
            else:
                print(f"❌ Generation failed: {result['error']}")
                return False
        else:
            print(f"❌ Request failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_video_generation()
TEST_SCRIPT

chmod +x /workspace/test_generation.py

# Setup systemd service (optional)
cat > /etc/systemd/system/skyreels-api.service << 'SERVICE'
[Unit]
Description=SkyReels API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/workspace
ExecStart=/workspace/start_api.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

echo ""
echo "========================================="
echo "✅ RUNPOD SETUP COMPLETE!"
echo "========================================="
echo ""
echo "📝 Next Steps:"
echo "1. Start the API server:"
echo "   ./start_api.sh"
echo ""
echo "2. Test the server (in another terminal):"
echo "   python3 health_check.py"
echo "   python3 test_generation.py"
echo ""
echo "3. Get the public URL:"
echo "   echo 'https://[your-pod-id].runpod.io'"
echo ""
echo "4. Add this URL to your Digital Ocean .env file:"
echo "   RUNPOD_SKYREELS_ENDPOINT=https://[your-pod-id].runpod.io"
echo ""
echo "🎬 Your RunPod GPU is ready for video generation!"
echo "========================================="