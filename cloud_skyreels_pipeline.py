# Cloud-Based SkyReels Video Generation Pipeline
# Works on RunPod/Vast.ai with SkyReels models
# Can be used for both book content AND work projects

import os
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import torch
from diffusers import DiffusionPipeline

class SkyReelsVideoGenerator:
    """
    Cloud GPU-optimized video generator using SkyReels
    Supports both book content and custom work projects
    """
    
    def __init__(self, model_version="v1", model_path="./models/skyreels"):
        self.model_version = model_version
        self.model_path = model_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipeline = None
        
    def load_model(self):
        """Load SkyReels model - call this once at start of session"""
        print(f"Loading SkyReels {self.model_version} on {self.device}...")
        
        if self.model_version == "v1":
            # Load SkyReels-V1 for human-centric videos
            self.pipeline = DiffusionPipeline.from_pretrained(
                f"{self.model_path}/skyreels-v1",
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                variant="fp16" if self.device == "cuda" else None
            )
        else:
            # Load SkyReels-V2 for unlimited length videos
            from skyreels_v2 import SkyReelsV2Pipeline
            self.pipeline = SkyReelsV2Pipeline.from_pretrained(
                f"{self.model_path}/skyreels-v2",
                torch_dtype=torch.float16
            )
        
        if self.device == "cuda":
            self.pipeline = self.pipeline.to("cuda")
            # Enable memory optimizations
            self.pipeline.enable_model_cpu_offload()
            self.pipeline.enable_vae_slicing()
            
        print("Model loaded successfully!")
        
    def generate_video(self, 
                      prompt: str, 
                      duration_seconds: int = 10,
                      fps: int = 24,
                      resolution: str = "540p",
                      character_image: Optional[str] = None) -> str:
        """
        Generate a single video clip
        
        Args:
            prompt: Text description of the scene
            duration_seconds: Video length (V2 supports unlimited)
            fps: Frames per second (24 recommended)
            resolution: "540p" or "720p" 
            character_image: Optional reference image for consistency
            
        Returns:
            Path to generated video file
        """
        
        # Prepare prompt with FPS prefix for V1
        if self.model_version == "v1":
            prompt = f"FPS-24, {prompt}"
            
        # Set resolution
        if resolution == "720p":
            height, width = 720, 1280
        else:  # 540p default
            height, width = 540, 960
            
        # For portrait videos (TikTok/Shorts)
        if "portrait" in prompt.lower() or "vertical" in prompt.lower():
            height, width = width, height  # Swap for 9:16 aspect
            
        print(f"Generating {duration_seconds}s video at {resolution}...")
        
        # Generate video
        if self.model_version == "v2" and duration_seconds > 10:
            # V2 supports unlimited length through extension
            video = self.pipeline(
                prompt=prompt,
                num_frames=fps * duration_seconds,
                height=height,
                width=width,
                num_inference_steps=50,
                guidance_scale=7.5,
                generator=torch.manual_seed(42)
            ).frames[0]
        else:
            # Standard generation
            video = self.pipeline(
                prompt=prompt,
                num_frames=min(fps * duration_seconds, 97),  # V1 limit
                height=height,
                width=width,
                num_inference_steps=30,
                guidance_scale=7.5
            ).frames[0]
            
        # Save video
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"output/video_{timestamp}.mp4"
        
        # Export frames to video
        self.export_to_video(video, output_path, fps)
        
        return output_path
        
    def export_to_video(self, frames, output_path, fps=24):
        """Export frames to MP4 video"""
        import cv2
        import numpy as np
        
        height, width = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        for frame in frames:
            if isinstance(frame, torch.Tensor):
                frame = frame.cpu().numpy()
            frame = (frame * 255).astype(np.uint8)
            out.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            
        out.release()
        print(f"Video saved to {output_path}")
        
    def batch_generate_videos(self, scripts: List[Dict], output_dir: str = "batch_output"):
        """
        Generate multiple videos in one session (cost-efficient)
        
        Args:
            scripts: List of video scripts with prompts and metadata
            output_dir: Directory for batch output
        """
        Path(output_dir).mkdir(exist_ok=True)
        
        results = []
        total_start = time.time()
        
        print(f"Starting batch generation of {len(scripts)} videos...")
        
        for i, script in enumerate(scripts, 1):
            print(f"\n[{i}/{len(scripts)}] Generating: {script.get('title', 'Untitled')}")
            
            try:
                video_path = self.generate_video(
                    prompt=script['prompt'],
                    duration_seconds=script.get('duration', 10),
                    resolution=script.get('resolution', '540p')
                )
                
                # Move to output directory with meaningful name
                final_path = f"{output_dir}/{script.get('filename', f'video_{i}')}.mp4"
                os.rename(video_path, final_path)
                
                results.append({
                    'title': script.get('title'),
                    'path': final_path,
                    'status': 'success'
                })
                
            except Exception as e:
                print(f"Error generating video: {e}")
                results.append({
                    'title': script.get('title'),
                    'status': 'failed',
                    'error': str(e)
                })
                
        total_time = time.time() - total_start
        print(f"\nBatch complete! Generated {len(results)} videos in {total_time/60:.1f} minutes")
        
        # Save batch report
        report_path = f"{output_dir}/batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump({
                'total_videos': len(results),
                'successful': sum(1 for r in results if r.get('status') == 'success'),
                'failed': sum(1 for r in results if r.get('status') == 'failed'),
                'total_time_minutes': total_time / 60,
                'results': results
            }, f, indent=2)
            
        return results


class CloudVideoOrchestrator:
    """
    Orchestrates video generation for both book content and work projects
    Optimized for cloud GPU usage (1-2 hour sessions)
    """
    
    def __init__(self, project_type="book", content_source=None):
        self.project_type = project_type  # "book" or "work"
        self.content_source = content_source
        self.generator = SkyReelsVideoGenerator(model_version="v2")  # V2 for unlimited length
        
    def prepare_weekly_batch(self):
        """Prepare all videos for the week in one batch"""
        
        if self.project_type == "book":
            return self.prepare_book_videos()
        else:
            return self.prepare_work_videos()
            
    def prepare_book_videos(self):
        """Prepare book-based video scripts"""
        scripts = []
        
        # Load book chapters
        chapters = self.load_book_chapters()
        
        for chapter in chapters[:7]:  # 7 videos for the week
            # Generate script for each chapter
            script = {
                'title': f"Chapter {chapter['number']}: {chapter['title']}",
                'prompt': self.create_book_prompt(chapter['content']),
                'duration': 30,  # Can go longer with V2!
                'resolution': '540p',
                'filename': f"book_ch{chapter['number']:02d}"
            }
            scripts.append(script)
            
        return scripts
        
    def prepare_work_videos(self):
        """Prepare work project videos"""
        # Customize this for your work needs
        scripts = []
        
        # Example: Product demos, tutorials, marketing content
        work_content = self.load_work_content()
        
        for item in work_content:
            script = {
                'title': item['title'],
                'prompt': item['description'],
                'duration': item.get('duration', 15),
                'resolution': '720p',  # Higher quality for work
                'filename': item['id']
            }
            scripts.append(script)
            
        return scripts
        
    def create_book_prompt(self, chapter_content):
        """Convert book content to video prompt"""
        # Enhanced prompt for cinematic quality
        prompt = f"""
        Cinematic adaptation, portrait vertical format for social media.
        Dynamic action scene with characters in motion.
        {chapter_content[:500]}
        High quality, professional cinematography, dramatic lighting.
        """
        return prompt
        
    def load_book_chapters(self):
        """Load chapters from EPUB or text files"""
        # Implementation depends on your book format
        # This is a placeholder
        return [
            {'number': 1, 'title': 'The Beginning', 'content': 'Chapter content...'},
            # Add more chapters
        ]
        
    def load_work_content(self):
        """Load work project content"""
        # Customize for your work needs
        return []
        
    def run_weekly_generation(self):
        """
        Main function to run on cloud GPU
        Generates all videos for the week in one session
        """
        print("=" * 60)
        print(f"WEEKLY VIDEO GENERATION - {self.project_type.upper()} PROJECT")
        print("=" * 60)
        
        # Load model once
        self.generator.load_model()
        
        # Prepare batch
        scripts = self.prepare_weekly_batch()
        
        # Generate all videos
        results = self.generator.batch_generate_videos(scripts)
        
        # Summary
        successful = sum(1 for r in results if r.get('status') == 'success')
        print(f"\n✅ Generated {successful}/{len(scripts)} videos successfully!")
        
        return results


# Main execution script for cloud GPU
if __name__ == "__main__":
    import sys
    
    # Check if running on GPU
    if not torch.cuda.is_available():
        print("WARNING: No GPU detected! This will be very slow.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Get project type
    project_type = input("Project type (book/work): ").lower()
    
    # Create orchestrator
    orchestrator = CloudVideoOrchestrator(project_type=project_type)
    
    # Run weekly batch
    results = orchestrator.run_weekly_generation()
    
    print("\n📹 Weekly video generation complete!")
    print("Videos are ready in the batch_output directory")
    print("Total cloud GPU time used: Check RunPod dashboard")