"""
RunPod API Client for SkyReels Video Generation
This handles all communication with RunPod GPU instances
"""

import os
import json
import asyncio
import httpx
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class RunPodClient:
    """Client for managing RunPod GPU instances and video generation"""
    
    def __init__(self):
        self.api_key = os.getenv("RUNPOD_API_KEY")
        self.base_url = "https://api.runpod.io/v2"
        self.skyreels_endpoint = os.getenv("RUNPOD_SKYREELS_ENDPOINT")
        self.pod_id = os.getenv("RUNPOD_POD_ID")
        
    async def start_pod(self) -> Dict:
        """Start the RunPod instance if it's stopped"""
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            # Check pod status
            response = await client.get(
                f"{self.base_url}/pod/{self.pod_id}",
                headers=headers
            )
            pod_info = response.json()
            
            if pod_info["status"] == "STOPPED":
                # Start the pod
                response = await client.post(
                    f"{self.base_url}/pod/{self.pod_id}/start",
                    headers=headers
                )
                
                # Wait for pod to be ready
                await self._wait_for_pod_ready()
                
                return {"status": "started", "pod_id": self.pod_id}
            
            return {"status": "already_running", "pod_id": self.pod_id}
    
    async def stop_pod(self) -> Dict:
        """Stop the RunPod instance to save costs"""
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            response = await client.post(
                f"{self.base_url}/pod/{self.pod_id}/stop",
                headers=headers
            )
            
            return {"status": "stopped", "pod_id": self.pod_id}
    
    async def generate_video(self, 
                           prompt: str,
                           duration_seconds: int = 10,
                           resolution: str = "720p") -> Dict:
        """Generate video using SkyReels on RunPod"""
        
        # Ensure pod is running
        await self.start_pod()
        
        # Prepare request
        payload = {
            "prompt": prompt,
            "duration": duration_seconds,
            "resolution": resolution,
            "fps": 24,
            "model": "skyreels-v2"
        }
        
        async with httpx.AsyncClient(timeout=600.0) as client:  # 10 min timeout
            try:
                # Call SkyReels API on RunPod
                response = await client.post(
                    f"{self.skyreels_endpoint}/generate",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "video_url": result["video_url"],
                        "generation_time": result["generation_time"],
                        "cost": self._calculate_cost(result["generation_time"])
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Generation failed: {response.text}"
                    }
                    
            except httpx.TimeoutException:
                return {
                    "success": False,
                    "error": "Video generation timed out (>10 minutes)"
                }
            except Exception as e:
                logger.error(f"Video generation error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
    
    async def generate_film(self,
                           storyboard: List[Dict],
                           title: str) -> Dict:
        """Generate a complete film from storyboard"""
        
        # Start pod
        await self.start_pod()
        
        # Generate scenes in parallel (up to 3 at a time)
        scenes = []
        for i in range(0, len(storyboard), 3):
            batch = storyboard[i:i+3]
            tasks = [
                self.generate_video(
                    scene["prompt"],
                    scene["duration"],
                    scene.get("resolution", "720p")
                )
                for scene in batch
            ]
            
            results = await asyncio.gather(*tasks)
            scenes.extend(results)
        
        # Assemble film on RunPod
        assembly_result = await self._assemble_film(scenes, title)
        
        # Stop pod to save costs
        await self.stop_pod()
        
        return assembly_result
    
    async def _assemble_film(self, scenes: List[Dict], title: str) -> Dict:
        """Assemble scenes into final film"""
        
        payload = {
            "scenes": [s["video_url"] for s in scenes if s["success"]],
            "title": title,
            "format": "mp4",
            "resolution": "1080p"
        }
        
        async with httpx.AsyncClient(timeout=1800.0) as client:  # 30 min timeout
            response = await client.post(
                f"{self.skyreels_endpoint}/assemble",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "film_url": result["film_url"],
                    "duration": result["duration"],
                    "size_mb": result["size_mb"]
                }
            else:
                return {
                    "success": False,
                    "error": f"Assembly failed: {response.text}"
                }
    
    async def _wait_for_pod_ready(self, max_wait: int = 300):
        """Wait for pod to be ready (max 5 minutes)"""
        
        start_time = datetime.now()
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            while (datetime.now() - start_time).seconds < max_wait:
                response = await client.get(
                    f"{self.base_url}/pod/{self.pod_id}",
                    headers=headers
                )
                pod_info = response.json()
                
                if pod_info["status"] == "RUNNING":
                    # Check if SkyReels API is responding
                    try:
                        health_response = await client.get(
                            f"{self.skyreels_endpoint}/health"
                        )
                        if health_response.status_code == 200:
                            return True
                    except:
                        pass
                
                await asyncio.sleep(10)
        
        raise TimeoutError("Pod did not become ready in time")
    
    def _calculate_cost(self, generation_time_seconds: int) -> float:
        """Calculate GPU cost for generation"""
        
        # Assuming RTX 4090 at $0.44/hour
        hourly_rate = 0.44
        hours = generation_time_seconds / 3600
        return round(hours * hourly_rate, 4)
    
    async def get_pod_status(self) -> Dict:
        """Get current pod status and costs"""
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            response = await client.get(
                f"{self.base_url}/pod/{self.pod_id}",
                headers=headers
            )
            
            pod_info = response.json()
            
            return {
                "pod_id": self.pod_id,
                "status": pod_info["status"],
                "gpu_type": pod_info.get("gpu_type", "Unknown"),
                "runtime_hours": pod_info.get("runtime", 0) / 3600,
                "estimated_cost": pod_info.get("runtime", 0) / 3600 * 0.44
            }


class RunPodManager:
    """Manages multiple RunPod instances for scaling"""
    
    def __init__(self):
        self.client = RunPodClient()
        self.active_pods = []
        
    async def scale_up(self, count: int = 1) -> List[str]:
        """Launch additional RunPod instances"""
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.client.api_key}"}
            
            new_pods = []
            for i in range(count):
                # Create new pod
                payload = {
                    "name": f"sysrai-worker-{datetime.now().timestamp()}",
                    "image_name": "runpod/pytorch:2.1.0-py3.10-cuda12.1.0-devel",
                    "gpu_type_id": "NVIDIA RTX 4090",
                    "cloud_type": "SECURE",
                    "container_disk_in_gb": 50,
                    "volume_in_gb": 100,
                    "ports": "8000/http,22/tcp",
                    "env": {
                        "SKYREELS_MODEL": "v2",
                        "API_MODE": "true"
                    }
                }
                
                response = await client.post(
                    f"{self.client.base_url}/pods",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    pod_id = response.json()["id"]
                    new_pods.append(pod_id)
                    self.active_pods.append(pod_id)
            
            return new_pods
    
    async def scale_down(self, count: int = 1):
        """Terminate RunPod instances"""
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.client.api_key}"}
            
            # Terminate oldest pods first
            pods_to_terminate = self.active_pods[:count]
            
            for pod_id in pods_to_terminate:
                await client.delete(
                    f"{self.client.base_url}/pods/{pod_id}",
                    headers=headers
                )
                self.active_pods.remove(pod_id)
    
    async def get_least_busy_pod(self) -> str:
        """Get the pod with lowest current load"""
        
        # For now, simple round-robin
        # In production, check actual pod metrics
        if not self.active_pods:
            await self.scale_up(1)
        
        return self.active_pods[0]