"""
Configuration settings for Sysrai Platform
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # App Info
    app_name: str = "Sysrai AI Film Platform"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./sysrai.db")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # JWT Authentication
    jwt_secret_key: str = "change-this-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    
    # RunPod
    runpod_api_key: str = ""
    runpod_skyreels_endpoint: str = ""
    runpod_pod_id: str = ""
    
    # Storage Paths (for containerized environment)
    storage_path: str = os.getenv("STORAGE_PATH", "/app/uploads")
    video_output_path: str = os.getenv("VIDEO_OUTPUT_PATH", "/app/videos")
    temp_path: str = os.getenv("TEMP_PATH", "/app/temp")
    
    # S3-compatible storage (optional - can use Hetzner Object Storage)
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "sysrai-videos"
    s3_region: str = "fsn1"
    s3_endpoint: str = ""  # Will be set if using Hetzner Object Storage
    
    # Email
    email_api_key: str = ""
    email_from: str = "noreply@sysrai.ai"
    
    # Admin
    admin_email: str = "admin@sysrai.ai"
    admin_password: str = "change_this_password"
    
    # Feature Flags
    enable_payments: bool = True
    enable_email: bool = True
    enable_analytics: bool = True
    
    # Pricing
    free_credits_on_signup: float = 10.0
    referral_bonus_credits: float = 25.0
    
    # RunPod Settings
    auto_stop_idle_pods: bool = True
    max_generation_time_minutes: int = 60
    default_gpu_type: str = "RTX 4090"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings():
    """Get cached settings instance"""
    return Settings()