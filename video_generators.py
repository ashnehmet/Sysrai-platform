"""
Alternative video generation APIs with better control over duration and aspect ratio
"""

import requests
import json
import base64
import os
import time
from typing import Optional, Dict, Any

def generate_with_runwayml(prompt: str, scene_number: int, duration: int = 10, aspect_ratio: str = "9:16") -> Optional[str]:
    """
    Generate video using RunwayML Gen-3 API
    Better control over duration and aspect ratio
    """
    url = "https://api.runwayml.com/v1/generations"
    
    headers = {
        'Authorization': f'Bearer {os.getenv("RUNWAYML_API_KEY")}',
        'Content-Type': 'application/json'
    }
    
    data = {
        "prompt": prompt,
        "model": "gen3a_turbo",
        "aspect_ratio": aspect_ratio,  # "9:16", "16:9", "1:1"
        "duration": duration,  # 5 or 10 seconds
        "seed": None,
        "resolution": "720p"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=300)
        response.raise_for_status()
        
        result = response.json()
        task_id = result['id']
        
        # Poll for completion
        while True:
            status_response = requests.get(f"{url}/{task_id}", headers=headers)
            status_data = status_response.json()
            
            if status_data['status'] == 'SUCCEEDED':
                video_url = status_data['output'][0]['url']
                
                # Download video
                video_response = requests.get(video_url)
                video_path = f"temp_clips/scene_{scene_number}.mp4"
                
                with open(video_path, 'wb') as f:
                    f.write(video_response.content)
                
                print(f"RunwayML video generated: {video_path}")
                return video_path
                
            elif status_data['status'] == 'FAILED':
                print(f"RunwayML generation failed: {status_data.get('error', 'Unknown error')}")
                return None
            
            # Wait before polling again
            time.sleep(10)
            
    except Exception as e:
        print(f"Error with RunwayML: {e}")
        return None

def generate_with_pika_labs(prompt: str, scene_number: int, duration: int = 10, aspect_ratio: str = "9:16") -> Optional[str]:
    """
    Generate video using Pika Labs API
    """
    url = "https://api.pika.art/generate/video"
    
    headers = {
        'Authorization': f'Bearer {os.getenv("PIKA_API_KEY")}',
        'Content-Type': 'application/json'
    }
    
    # Convert aspect ratio to Pika format
    pika_aspect = "vertical" if aspect_ratio == "9:16" else "horizontal"
    
    data = {
        "prompt": prompt,
        "aspect_ratio": pika_aspect,
        "duration": duration,
        "fps": 24,
        "motion": 1,  # Motion strength 1-4
        "seed": None
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=300)
        response.raise_for_status()
        
        result = response.json()
        job_id = result['job_id']
        
        # Poll for completion
        while True:
            status_response = requests.get(f"https://api.pika.art/jobs/{job_id}", headers=headers)
            status_data = status_response.json()
            
            if status_data['status'] == 'completed':
                video_url = status_data['result']['video_url']
                
                # Download video
                video_response = requests.get(video_url)
                video_path = f"temp_clips/scene_{scene_number}.mp4"
                
                with open(video_path, 'wb') as f:
                    f.write(video_response.content)
                
                print(f"Pika Labs video generated: {video_path}")
                return video_path
                
            elif status_data['status'] == 'failed':
                print(f"Pika Labs generation failed: {status_data.get('error', 'Unknown error')}")
                return None
            
            time.sleep(15)
            
    except Exception as e:
        print(f"Error with Pika Labs: {e}")
        return None

def generate_with_stability_ai(prompt: str, scene_number: int, duration: int = 10, aspect_ratio: str = "9:16") -> Optional[str]:
    """
    Generate video using Stability AI Video API
    """
    url = "https://api.stability.ai/v2beta/video/generate"
    
    headers = {
        'Authorization': f'Bearer {os.getenv("STABILITY_API_KEY")}',
        'Content-Type': 'application/json'
    }
    
    # Convert aspect ratio to width/height
    if aspect_ratio == "9:16":
        width, height = 576, 1024
    elif aspect_ratio == "16:9":
        width, height = 1024, 576
    else:
        width, height = 1024, 1024
    
    data = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "duration": duration,
        "fps": 24,
        "motion_bucket_id": 127,  # Motion strength
        "seed": None
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=300)
        response.raise_for_status()
        
        result = response.json()
        generation_id = result['id']
        
        # Poll for completion
        while True:
            status_response = requests.get(f"https://api.stability.ai/v2beta/video/generate/{generation_id}", headers=headers)
            status_data = status_response.json()
            
            if status_data['status'] == 'complete':
                video_url = status_data['video']
                
                # Download video
                video_response = requests.get(video_url)
                video_path = f"temp_clips/scene_{scene_number}.mp4"
                
                with open(video_path, 'wb') as f:
                    f.write(video_response.content)
                
                print(f"Stability AI video generated: {video_path}")
                return video_path
                
            elif status_data['status'] == 'failed':
                print(f"Stability AI generation failed: {status_data.get('error', 'Unknown error')}")
                return None
            
            time.sleep(15)
            
    except Exception as e:
        print(f"Error with Stability AI: {e}")
        return None

# Universal video generator that tries different APIs
def generate_video_flexible(prompt: str, scene_number: int, duration: int = 10, aspect_ratio: str = "9:16", preferred_api: str = "runwayml") -> Optional[str]:
    """
    Generate video using the best available API with fallback options
    """
    # List of generators in order of preference
    generators = {
        "runwayml": generate_with_runwayml,
        "pika": generate_with_pika_labs,
        "stability": generate_with_stability_ai,
        "google_veo2": generate_with_google_veo2
    }
    
    # Try preferred API first
    if preferred_api in generators:
        print(f"Trying {preferred_api} for scene {scene_number}...")
        result = generators[preferred_api](prompt, scene_number, duration, aspect_ratio)
        if result:
            return result
    
    # Try other APIs as fallbacks
    for api_name, generator in generators.items():
        if api_name != preferred_api:
            print(f"Fallback: Trying {api_name} for scene {scene_number}...")
            result = generator(prompt, scene_number, duration, aspect_ratio)
            if result:
                return result
    
    print(f"All video generation APIs failed for scene {scene_number}")
    return None

def generate_with_google_veo2(prompt: str, scene_number: int, duration: int = 8, aspect_ratio: str = "9:16") -> Optional[str]:
    """
    Generate video using Google Veo2 API via Vertex AI
    High quality but expensive ($0.50 per second)
    """
    try:
        from google.cloud import aiplatform
        from vertexai.generative_models import GenerativeModel, Part
        import vertexai
        
        # Initialize Vertex AI
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        
        if not project_id:
            print("Google Cloud Project ID not configured")
            return None
            
        vertexai.init(project=project_id, location=location)
        
        # Create Veo2 model
        model = GenerativeModel("veo-2.0-generate-001")
        
        # Prepare request
        enhanced_prompt = f"""
        Create a {duration}-second video clip in {aspect_ratio} aspect ratio:
        {prompt}
        
        Requirements:
        - Vertical portrait format for mobile viewing
        - 720p resolution, 24fps
        - Smooth camera movement and realistic physics
        - High production value
        """
        
        # Generate video
        print(f"Generating video with Google Veo2 (${0.50 * duration} cost)...")
        response = model.generate_content([enhanced_prompt])
        
        if response and response.candidates:
            # Extract video data (this will need to be adjusted based on actual API response)
            video_data = response.candidates[0].content
            
            # Save video file
            video_path = f"temp_clips/scene_{scene_number}_veo2.mp4"
            with open(video_path, 'wb') as f:
                f.write(video_data)
            
            print(f"Veo2 video generated: {video_path}")
            return video_path
        
        return None
        
    except ImportError:
        print("Google Cloud AI libraries not installed. Run: pip install google-cloud-aiplatform vertexai")
        return None
    except Exception as e:
        print(f"Google Veo2 generation failed: {e}")
        return None

# API key validation
def check_api_keys():
    """Check which video generation APIs are available"""
    available_apis = []
    
    if os.getenv("RUNWAYML_API_KEY"):
        available_apis.append("runwayml")
    
    if os.getenv("PIKA_API_KEY"):
        available_apis.append("pika")
        
    if os.getenv("STABILITY_API_KEY"):
        available_apis.append("stability")
    
    if os.getenv("SEGMIND_API_KEY"):
        available_apis.append("segmind")
    
    if os.getenv("GOOGLE_CLOUD_PROJECT_ID"):
        available_apis.append("google_veo2")
    
    return available_apis