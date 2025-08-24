#!/usr/bin/env python3
"""
RunPod Controller - Auto Start/Stop GPU Pods
Manages RunPod instances to minimize costs
"""

import os
import json
import time
import asyncio
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RunPodController:
    """Manages RunPod GPU instances for cost optimization"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.runpod.io/v2"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Pod configuration
        self.pod_config = {
            "cloudType": "SECURE",
            "gpuType": "RTX 4090",  # Most cost-effective
            "templateId": None,  # Set this to your template ID
            "name": "sysrai-skyreels-api",
            "containerDiskInGb": 50,
            "volumeInGb": 100,
            "ports": "8000/http,22/tcp",
            "env": [
                {"key": "SYSRAI_API_MODE", "value": "production"}
            ]
        }
        
        # Cost control settings
        self.max_idle_time = 300  # 5 minutes idle before shutdown
        self.startup_timeout = 600  # 10 minutes max startup time
        self.active_pods = {}  # Track active pods
        
    async def start_pod_for_job(self, job_id: str, priority: int = 1) -> Dict:
        """Start a new pod for video generation job"""
        
        logger.info(f"Starting pod for job {job_id} (priority: {priority})")
        
        try:
            # Choose GPU type based on priority
            if priority >= 3:  # Urgent
                self.pod_config["gpuType"] = "A100 40GB"
            elif priority >= 2:  # High
                self.pod_config["gpuType"] = "RTX 4090"
            else:  # Normal
                self.pod_config["gpuType"] = "RTX 4090"
            
            # Create pod
            response = requests.post(
                f"{self.base_url}/pods",
                headers=self.headers,
                json=self.pod_config
            )
            response.raise_for_status()
            
            pod_data = response.json()
            pod_id = pod_data["id"]
            
            # Track the pod
            self.active_pods[pod_id] = {
                "job_id": job_id,
                "started_at": datetime.utcnow(),
                "status": "starting",
                "gpu_type": self.pod_config["gpuType"],
                "priority": priority
            }
            
            logger.info(f"Pod {pod_id} starting for job {job_id}")
            
            # Wait for pod to be ready
            pod_url = await self._wait_for_pod_ready(pod_id)
            
            return {
                "pod_id": po