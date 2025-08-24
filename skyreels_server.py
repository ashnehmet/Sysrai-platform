"""
SkyReels API Server for RunPod
This file should be deployed on the RunPod GPU instance
"""

import os
import torch
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
import uvicorn

# Check if we have GPU
if not torch.cuda.is_available():
    print("WARNING: No GPU detected! SkyReels requires CUDA")

app = FastAPI(title="SkyReels API Server", version="1.0.0")

class VideoRequest(BaseModel):
    prompt: str
    duration: int = 10
    resolution: str = "720p"
    fps: int = 24
    model: str = "skyreels-v2"

class FilmRequest(BaseModel):
    scenes: List[Dict]
    title: str
    format: str = "mp4"
    resolution: str = "1080p"

# Global model instance
skyreels_model = None
model_loaded = False

@app.on_event("startup")
async def load_skyreels_model():
    """Load SkyReels model on startup"""
    global skyreels_model, model_loaded
    
    try:
        print("🤖 Loading SkyReels V2 model...")
        
        # Import SkyReels after GPU check
        from diffusers import DiffusionPipeline
        
        model_path = "/workspace/models/skyreels-v2"
        
        if not Path(model_path).exists():
            print("❌ Model not found. Please run download_models.py first")
            return
            
        skyreels_model = DiffusionPipeline.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            variant="fp16"
        )
        
        skyreels_model = skyreels_model.to("cuda")
        skyreels_model.enable_model_cpu_offload()
        skyreels_model.enable_vae_slicing()
        
        model_loaded = True
        print("✅ SkyReels model loaded successfully!")
        
    except Exception as e:
        print(f"❌ Failed to load SkyReels model: {e}")
        model_loaded = False

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": model_loaded,
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "vram_gb": torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else 0
    }

@app.post("/generate")
async def generate_video(request: VideoRequest):
    """Generate a single video clip"""
    
    if not model_loaded:
        raise HTTPException(status_code=503, detail="SkyReels model not loaded")
    
    try:
        start_time = datetime.now()
        
        # Prepare prompt for SkyReels
        prompt = f"FPS-{request.fps}, {request.prompt}"
        
        # Set resolution
        if request.resolution == "720p":
            height, width = 720, 1280
        elif request.resolution == "1080p":
            height, width = 1080, 1920
        else:  # 540p default
            height, width = 540, 960
            
        # Generate video
        print(f"🎬 Generating {request.duration}s video: {request.prompt[:50]}...")
        
        video_frames = skyreels_model(
            prompt=prompt,
            num_frames=request.fps * request.duration,
            height=height,
            width=width,
            num_inference_steps=50,
            guidance_scale=7.5,
            generator=torch.manual_seed(42)
        ).frames[0]
        
        # Save video
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"/workspace/output/video_{timestamp}.mp4"
        
        # Convert frames to video
        save_video_frames(video_frames, output_path, request.fps)
        
        generation_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "success": True,
            "video_url": f"/download/{output_path.split('/')[-1]}",
            "generation_time": generation_time,
            "resolution": f"{width}x{height}",
            "duration": request.duration
        }
        
    except Exception as e:
        print(f"❌ Video generation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/assemble")
async def assemble_film(request: FilmRequest):
    """Assemble multiple scenes into a complete film"""
    
    try:
        from moviepy import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
        
        start_time = datetime.now()
        
        # Load all scene videos
        clips = []
        total_duration = 0
        
        for i, scene_url in enumerate(request.scenes):
            # Download or load scene video
            scene_path = scene_url.replace("/download/", "/workspace/output/")
            
            if Path(scene_path).exists():
                clip = VideoFileClip(scene_path)
                clips.append(clip)
                total_duration += clip.duration
                print(f"📹 Loaded scene {i+1}: {clip.duration}s")
            else:
                print(f"⚠️ Scene {i+1} not found: {scene_path}")
        
        if not clips:
            raise HTTPException(status_code=400, detail="No valid scenes found")
        
        # Concatenate all scenes
        print("🎞️ Assembling film...")
        final_film = concatenate_videoclips(clips)
        
        # Add title card if requested
        if request.title:
            title_clip = TextClip(
                f"{request.title}\n\nGenerated with SkyReels AI",
                font_size=48,
                color='white',
                size=final_film.size,
                method='caption'
            ).with_duration(3).with_fps(24)
            
            final_film = concatenate_videoclips([title_clip, final_film])
        
        # Export film
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        film_path = f"/workspace/output/film_{timestamp}.{request.format}"
        
        final_film.write_videofile(
            film_path,
            codec='libx264',
            audio_codec='aac',
            fps=24
        )
        
        # Get file size
        file_size = Path(film_path).stat().st_size / (1024 * 1024)  # MB
        
        generation_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "success": True,
            "film_url": f"/download/{film_path.split('/')[-1]}",
            "duration": total_duration + (3 if request.title else 0),
            "size_mb": round(file_size, 2),
            "assembly_time": generation_time
        }
        
    except Exception as e:
        print(f"❌ Film assembly failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated video files"""
    
    file_path = f"/workspace/output/{filename}"
    
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    from fastapi.responses import FileResponse
    return FileResponse(file_path)

def save_video_frames(frames, output_path: str, fps: int = 24):
    """Convert video frames to MP4 file"""
    
    import cv2
    import numpy as np
    
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Get frame dimensions
    if hasattr(frames[0], 'shape'):
        height, width = frames[0].shape[:2]
    else:
        # Convert PIL to numpy if needed
        frames = [np.array(frame) for frame in frames]
        height, width = frames[0].shape[:2]
    
    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Write frames
    for frame in frames:
        if isinstance(frame, torch.Tensor):
            frame = frame.cpu().numpy()
        
        # Ensure frame is in the right format
        if frame.dtype != np.uint8:
            frame = (frame * 255).astype(np.uint8)
        
        # Convert RGB to BGR for OpenCV
        if frame.shape[-1] == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        out.write(frame)
    
    out.release()
    print(f"✅ Video saved: {output_path}")

@app.get("/models/download")
async def download_models():
    """Download SkyReels models (for initialization)"""
    
    try:
        from huggingface_hub import snapshot_download
        
        model_dir = "/workspace/models/skyreels-v2"
        Path(model_dir).mkdir(parents=True, exist_ok=True)
        
        print("⬇️ Downloading SkyReels V2 models...")
        
        # Download the 1.3B model (smallest, most compatible)
        snapshot_download(
            repo_id="SkyworkAI/SkyReels-V2-1.3B-540P",
            local_dir=model_dir,
            resume_download=True
        )
        
        return {
            "success": True,
            "message": "Models downloaded successfully",
            "path": model_dir
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # Create output directory
    Path("/workspace/output").mkdir(parents=True, exist_ok=True)
    
    print("🚀 Starting SkyReels API Server on RunPod...")
    print("📊 System Info:")
    print(f"  GPU Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  GPU Name: {torch.cuda.get_device_name(0)}")
        print(f"  GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    uvicorn.run(
        "skyreels_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )