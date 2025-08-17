#!/usr/bin/env python3
"""
SkyReels API Server for RunPod
Simple FastAPI wrapper around SkyReels V2 for video generation
"""

import os
import json
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import torch
import boto3
from botocore.exceptions import NoCredentialsError

app = FastAPI(title="SkyReels API Service", version="1.0.0")

# Global variables
SKYREELS_MODEL = None
OUTPUT_DIR = Path("/workspace/outputs")
MODEL_DIR = Path("/workspace/models")

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)

class VideoRequest(BaseModel):
    prompt: str
    duration_seconds: int = 30
    resolution: str = "720p"  # 720p, 1080p
    aspect_ratio: str = "16:9"  # 16:9, 9:16, 1:1
    user_id: str
    project_id: str
    priority: int = 1  # 1=normal, 2=high, 3=urgent

class VideoResponse(BaseModel):
    video_id: str
    status: str  # queued, processing, completed, failed
    video_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    cost_estimate: float
    estimated_completion: Optional[str] = None
    error_message: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    gpu_available: bool
    gpu_name: Optional[str] = None
    vram_gb: Optional[float] = None
    queue_size: int
    uptime_seconds: int

# Job queue for managing video generation
video_queue = []
processing_jobs = {}
completed_jobs = {}

@app.on_event("startup")
async def startup_event():
    """Initialize SkyReels model on startup"""
    global SKYREELS_MODEL
    
    print("Starting SkyReels API Service...")
    print(f"GPU Available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    # Initialize SkyReels model
    try:
        await load_skyreels_model()
        print("SkyReels model loaded successfully")
    except Exception as e:
        print(f"Error loading SkyReels model: {e}")
        # Don't fail startup - handle gracefully

async def load_skyreels_model():
    """Load SkyReels V2 model"""
    global SKYREELS_MODEL
    
    # Check if models exist
    if not MODEL_DIR.exists() or not any(MODEL_DIR.iterdir()):
        print("Downloading SkyReels V2 models...")
        await download_skyreels_models()
    
    # Load the model (placeholder - replace with actual SkyReels loading)
    # SKYREELS_MODEL = load_skyreels_v2_model(MODEL_DIR)
    print("SkyReels model loading simulated (replace with actual implementation)")

async def download_skyreels_models():
    """Download SkyReels V2 models from Hugging Face"""
    print("Downloading SkyReels V2 models (this may take 15-20 minutes)...")
    
    # Simulate download (replace with actual Hugging Face download)
    from huggingface_hub import snapshot_download
    
    try:
        # Determine model size based on VRAM
        if torch.cuda.is_available():
            vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
            if vram_gb < 20:
                model_repo = "SkyworkAI/SkyReels-V2-1.3B-540P"
            elif vram_gb < 50:
                model_repo = "SkyworkAI/SkyReels-V2-5B-540P"
            else:
                model_repo = "SkyworkAI/SkyReels-V2-14B-540P"
        else:
            model_repo = "SkyworkAI/SkyReels-V2-1.3B-540P"
        
        print(f"Downloading {model_repo}...")
        snapshot_download(
            repo_id=model_repo,
            local_dir=str(MODEL_DIR),
            resume_download=True
        )
        print("Models downloaded successfully")
        
    except Exception as e:
        print(f"Error downloading models: {e}")
        raise

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    uptime = 0  # Calculate actual uptime
    
    return HealthResponse(
        status="ready" if SKYREELS_MODEL else "loading",
        gpu_available=torch.cuda.is_available(),
        gpu_name=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        vram_gb=torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else 0,
        queue_size=len(video_queue),
        uptime_seconds=uptime
    )

@app.post("/generate-video", response_model=VideoResponse)
async def generate_video(request: VideoRequest, background_tasks: BackgroundTasks):
    """Queue video generation request"""
    
    video_id = str(uuid.uuid4())
    
    # Calculate cost estimate
    cost_estimate = calculate_cost(request.duration_seconds, request.resolution)
    
    # Create job
    job = {
        "video_id": video_id,
        "request": request,
        "status": "queued",
        "created_at": datetime.utcnow(),
        "cost_estimate": cost_estimate
    }
    
    # Add to queue
    video_queue.append(job)
    
    # Start processing in background
    background_tasks.add_task(process_video_queue)
    
    return VideoResponse(
        video_id=video_id,
        status="queued",
        cost_estimate=cost_estimate,
        estimated_completion=(datetime.utcnow().isoformat() + "Z")
    )

@app.get("/video/{video_id}", response_model=VideoResponse)
async def get_video_status(video_id: str):
    """Get video generation status"""
    
    # Check completed jobs
    if video_id in completed_jobs:
        job = completed_jobs[video_id]
        return VideoResponse(
            video_id=video_id,
            status=job["status"],
            video_url=job.get("video_url"),
            duration_seconds=job.get("duration_seconds"),
            cost_estimate=job["cost_estimate"],
            error_message=job.get("error_message")
        )
    
    # Check processing jobs
    if video_id in processing_jobs:
        job = processing_jobs[video_id]
        return VideoResponse(
            video_id=video_id,
            status="processing",
            cost_estimate=job["cost_estimate"],
            estimated_completion=job.get("estimated_completion")
        )
    
    # Check queue
    for job in video_queue:
        if job["video_id"] == video_id:
            return VideoResponse(
                video_id=video_id,
                status="queued",
                cost_estimate=job["cost_estimate"]
            )
    
    raise HTTPException(status_code=404, detail="Video not found")

@app.get("/download/{video_id}")
async def download_video(video_id: str):
    """Download generated video file"""
    
    if video_id not in completed_jobs:
        raise HTTPException(status_code=404, detail="Video not found or not ready")
    
    job = completed_jobs[video_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video not completed")
    
    video_path = OUTPUT_DIR / f"{video_id}.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=f"sysrai_video_{video_id}.mp4"
    )

@app.get("/queue")
async def get_queue_status():
    """Get current queue status"""
    return {
        "queue_size": len(video_queue),
        "processing": len(processing_jobs),
        "completed": len(completed_jobs)
    }

async def process_video_queue():
    """Background task to process video generation queue"""
    if not video_queue or SKYREELS_MODEL is None:
        return
    
    # Get next job
    job = video_queue.pop(0)
    video_id = job["video_id"]
    request = job["request"]
    
    # Move to processing
    processing_jobs[video_id] = job
    job["status"] = "processing"
    job["started_at"] = datetime.utcnow()
    
    try:
        # Generate video with SkyReels
        video_path = await generate_with_skyreels(request, video_id)
        
        # Upload to storage (optional)
        video_url = await upload_to_storage(video_path, video_id)
        
        # Mark as completed
        job["status"] = "completed"
        job["video_url"] = video_url
        job["duration_seconds"] = request.duration_seconds
        job["completed_at"] = datetime.utcnow()
        
        print(f"Video {video_id} completed successfully")
        
    except Exception as e:
        # Mark as failed
        job["status"] = "failed"
        job["error_message"] = str(e)
        job["failed_at"] = datetime.utcnow()
        
        print(f"Video {video_id} failed: {e}")
    
    finally:
        # Move from processing to completed
        completed_jobs[video_id] = processing_jobs.pop(video_id)

async def generate_with_skyreels(request: VideoRequest, video_id: str) -> str:
    """Generate video using SkyReels V2"""
    
    output_path = OUTPUT_DIR / f"{video_id}.mp4"
    
    # Prepare SkyReels parameters
    skyreels_params = {
        "prompt": request.prompt,
        "duration": request.duration_seconds,
        "resolution": request.resolution,
        "aspect_ratio": request.aspect_ratio,
        "output_path": str(output_path)
    }
    
    print(f"Generating video with SkyReels: {skyreels_params}")
    
    # TODO: Replace with actual SkyReels V2 inference
    # video = SKYREELS_MODEL.generate(**skyreels_params)
    
    # Simulate video generation for now
    await asyncio.sleep(10)  # Simulate processing time
    
    # Create dummy video file (replace with actual SkyReels output)
    with open(output_path, "wb") as f:
        f.write(b"dummy video content")
    
    return str(output_path)

async def upload_to_storage(video_path: str, video_id: str) -> str:
    """Upload video to S3 or similar storage"""
    
    # Check if S3 credentials are available
    try:
        s3_client = boto3.client('s3')
        bucket_name = os.getenv('S3_BUCKET_NAME', 'sysrai-videos')
        
        # Upload to S3
        key = f"videos/{video_id}.mp4"
        s3_client.upload_file(video_path, bucket_name, key)
        
        # Return public URL
        return f"https://{bucket_name}.s3.amazonaws.com/{key}"
        
    except (NoCredentialsError, Exception) as e:
        print(f"Storage upload failed: {e}")
        # Return local file URL as fallback
        return f"/download/{video_id}"

def calculate_cost(duration_seconds: int, resolution: str) -> float:
    """Calculate estimated cost for video generation"""
    
    # Base cost per second
    base_cost_per_second = {
        "720p": 0.10,
        "1080p": 0.15,
        "4K": 0.25
    }
    
    cost_per_second = base_cost_per_second.get(resolution, 0.10)
    return duration_seconds * cost_per_second

@app.post("/shutdown")
async def shutdown_pod():
    """Graceful shutdown - save state and terminate pod"""
    
    # Save current state
    state = {
        "video_queue": video_queue,
        "processing_jobs": processing_jobs,
        "completed_jobs": completed_jobs,
        "shutdown_time": datetime.utcnow().isoformat()
    }
    
    with open("/workspace/state.json", "w") as f:
        json.dump(state, f, default=str)
    
    print("State saved. Pod ready for shutdown.")
    
    return {"message": "Pod ready for shutdown", "jobs_saved": len(video_queue) + len(processing_jobs)}

if __name__ == "__main__":
    import uvicorn
    
    print("="*50)
    print("SYSRAI SKYREELS API SERVICE")
    print("="*50)
    print("Starting SkyReels API server...")
    print("Endpoint: http://0.0.0.0:8000")
    print("Health: http://0.0.0.0:8000/health")
    print("Docs: http://0.0.0.0:8000/docs")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
