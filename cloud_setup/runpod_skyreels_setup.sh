#!/bin/bash
# RunPod SkyReels Setup Script
# This script sets up SkyReels-V1 or V2 on RunPod GPU instance

echo "==================================="
echo "SkyReels Cloud GPU Setup for RunPod"
echo "==================================="

# Update system
apt-get update && apt-get upgrade -y

# Install system dependencies
apt-get install -y git wget ffmpeg python3.10 python3-pip cuda-toolkit-12-2

# Clone SkyReels repository (choose V1 or V2)
echo "Which version to install?"
echo "1) SkyReels-V1 (More stable, 24GB VRAM, human-focused)"
echo "2) SkyReels-V2 (Unlimited length, 14-51GB VRAM)"
read -p "Enter choice (1 or 2): " version_choice

if [ "$version_choice" = "1" ]; then
    echo "Installing SkyReels-V1..."
    git clone https://github.com/SkyworkAI/SkyReels-V1.git
    cd SkyReels-V1
else
    echo "Installing SkyReels-V2..."
    git clone https://github.com/SkyworkAI/SkyReels-V2.git
    cd SkyReels-V2
fi

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Download model weights from Hugging Face
echo "Downloading model weights..."
if [ "$version_choice" = "1" ]; then
    # V1 models
    python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='SkyworkAI/SkyReels-V1-Hunyuan-T2V', local_dir='./models/skyreels-v1')"
else
    # V2 models - choose smaller 1.3B model for cost efficiency
    python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='SkyworkAI/SkyReels-V2-1.3B-540P', local_dir='./models/skyreels-v2')"
fi

echo "Setup complete! SkyReels is ready to use."
echo "To generate videos, use: python generate_video.py"