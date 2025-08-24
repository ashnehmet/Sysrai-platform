"""
SkyReels Monetization Platform - User accounts, credits, and billing
"""

import os
import json
import stripe
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio
import aioredis
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import boto3

# Database models
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    credits = Column(Float, default=0.0)
    subscription_tier = Column(String, default="free")  # free, starter, pro, enterprise
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    total_spent = Column(Float, default=0.0)
    referral_code = Column(String, unique=True)
    referred_by = Column(String, nullable=True)
    api_key = Column(String, unique=True)
    webhook_url = Column(String, nullable=True)
    
class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    title = Column(String)
    duration_minutes = Column(Integer)
    format = Column(String)  # film, series, short
    status = Column(String)  # draft, queued, generating, complete, failed
    cost = Column(Float)
    credits_used = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    film_url = Column(String, nullable=True)
    metadata = Column(Text)  # JSON string
    
class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    type = Column(String)  # purchase, usage, refund, bonus
    amount = Column(Float)
    credits = Column(Float)
    description = Column(String)
    stripe_payment_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class GPUNode(Base):
    __tablename__ = "gpu_nodes"
    
    id = Column(String, primary_key=True)
    provider = Column(String)  # runpod, vast, lambda
    instance_id = Column(String)
    gpu_type = Column(String)  # rtx4090, a100_40gb, a100_80gb, h100
    hourly_cost = Column(Float)
    status = Column(String)  # available, busy, maintenance
    current_project_id = Column(String, nullable=True)
    performance_score = Column(Float, default=1.0)
    region = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_health_check = Column(DateTime)


# Platform configuration
class PlatformConfig:
    """Platform configuration and pricing"""
    
    # Stripe configuration
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    # JWT configuration  
    JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = 24
    
    # Pricing tiers
    SUBSCRIPTION_TIERS = {
        "free": {
            "monthly_price": 0,
            "included_credits": 10,
            "price_per_minute": 5.00,  # Higher price for free tier
            "max_duration_minutes": 10,
            "priority": 0,
            "features": ["basic_quality", "watermark"]
        },
        "starter": {
            "monthly_price": 29.99,
            "included_credits": 100,
            "price_per_minute": 3.00,
            "max_duration_minutes": 60,
            "priority": 1,
            "features": ["standard_quality", "no_watermark", "downloads"]
        },
        "pro": {
            "monthly_price": 99.99,
            "included_credits": 500,
            "price_per_minute": 2.50,
            "max_duration_minutes": 180,
            "priority": 2,
            "features": ["premium_quality", "no_watermark", "downloads", "api_access", "priority_queue"]
        },
        "enterprise": {
            "monthly_price": 499.99,
            "included_credits": 3000,
            "price_per_minute": 2.00,
            "max_duration_minutes": -1,  # Unlimited
            "priority": 3,
            "features": ["premium_quality", "no_watermark", "downloads", "api_access", 
                        "priority_queue", "dedicated_gpu", "sla", "custom_models"]
        }
    }
    
    # Credit packages
    CREDIT_PACKAGES = {
        "small": {"credits": 50, "price": 19.99, "bonus": 0},
        "medium": {"credits": 150, "price": 49.99, "bonus": 10},  # 10 bonus credits
        "large": {"credits": 500, "price": 149.99, "bonus": 50},   # 50 bonus credits
        "mega": {"credits": 2000, "price": 499.99, "bonus": 300},  # 300 bonus credits
    }


class AuthenticationService:
    """Handle user authentication and authorization"""
    
    def __init__(self):
        self.security = HTTPBearer()
        
    def hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', 
                                       password.encode('utf-8'),
                                       salt.encode('utf-8'),
                                       100000)
        return f"{salt}${pwd_hash.hex()}"
        
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        salt, pwd_hash = password_hash.split('$')
        test_hash = hashlib.pbkdf2_hmac('sha256',
                                        password.encode('utf-8'),
                                        salt.encode('utf-8'),
                                        100000)
        return test_hash.hex() == pwd_hash
        
    def create_access_token(self, user_id: str) -> str:
        """Create JWT access token"""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(hours=PlatformConfig.JWT_EXPIRATION_HOURS)
        }
        return jwt.encode(payload, PlatformConfig.JWT_SECRET, algorithm=PlatformConfig.JWT_ALGORITHM)
        
    def verify_token(self, token: str) -> Dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, PlatformConfig.JWT_SECRET, 
                               algorithms=[PlatformConfig.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")


class CreditManager:
    """Manage user credits and billing"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        stripe.api_key = PlatformConfig.STRIPE_SECRET_KEY
        
    async def purchase_credits(self, user_id: str, package: str) -> Dict:
        """Process credit purchase"""
        
        if package not in PlatformConfig.CREDIT_PACKAGES:
            raise ValueError("Invalid credit package")
            
        package_info = PlatformConfig.CREDIT_PACKAGES[package]
        total_credits = package_info['credits'] + package_info['bonus']
        
        # Create Stripe payment intent
        payment_intent = stripe.PaymentIntent.create(
            amount=int(package_info['price'] * 100),  # Stripe uses cents
            currency='usd',
            metadata={
                'user_id': user_id,
                'package': package,
                'credits': total_credits
            }
        )
        
        return {
            'payment_intent_id': payment_intent.id,
            'client_secret': payment_intent.client_secret,
            'credits': total_credits,
            'price': package_info['price']
        }
        
    async def apply_credits(self, user_id: str, credits: float, 
                           transaction_type: str, description: str) -> float:
        """Apply credits to user account"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
            
        user.credits += credits
        
        # Record transaction
        transaction = Transaction(
            id=secrets.token_hex(16),
            user_id=user_id,
            type=transaction_type,
            credits=credits,
            description=description
        )
        self.db.add(transaction)
        self.db.commit()
        
        return user.credits
        
    async def use_credits(self, user_id: str, project_id: str, 
                         duration_minutes: int) -> Dict:
        """Deduct credits for project generation"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
            
        # Calculate cost based on tier
        tier_info = PlatformConfig.SUBSCRIPTION_TIERS[user.subscription_tier]
        cost = duration_minutes * tier_info['price_per_minute']
        
        if user.credits < cost:
            raise ValueError(f"Insufficient credits. Need {cost}, have {user.credits}")
            
        # Deduct credits
        user.credits -= cost
        
        # Record usage
        transaction = Transaction(
            id=secrets.token_hex(16),
            user_id=user_id,
            type='usage',
            credits=-cost,
            description=f"Project {project_id}: {duration_minutes} minutes"
        )
        self.db.add(transaction)
        self.db.commit()
        
        return {
            'credits_used': cost,
            'remaining_credits': user.credits
        }


class GPUOrchestrator:
    """Manage GPU nodes and job distribution"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.providers = {
            'runpod': RunPodProvider(),
            'vast': VastAIProvider(),
            'lambda': LambdaLabsProvider()
        }
        
    async def scale_up(self, required_capacity: int) -> List[str]:
        """Scale up GPU capacity based on demand"""
        
        current_nodes = self.db.query(GPUNode).filter(
            GPUNode.status == 'available'
        ).count()
        
        if current_nodes >= required_capacity:
            return []
            
        nodes_to_add = required_capacity - current_nodes
        new_nodes = []
        
        # Prioritize cheapest providers
        for provider_name in ['vast', 'runpod', 'lambda']:
            if nodes_to_add <= 0:
                break
                
            provider = self.providers[provider_name]
            launched = await provider.launch_instances(
                count=min(nodes_to_add, 5),  # Max 5 per provider at once
                gpu_type='rtx4090'  # Start with cheapest
            )
            
            for instance in launched:
                node = GPUNode(
                    id=secrets.token_hex(8),
                    provider=provider_name,
                    instance_id=instance['instance_id'],
                    gpu_type=instance['gpu_type'],
                    hourly_cost=instance['hourly_cost'],
                    status='available',
                    region=instance['region']
                )
                self.db.add(node)
                new_nodes.append(node.id)
                nodes_to_add -= 1
                
        self.db.commit()
        return new_nodes
        
    async def scale_down(self, excess_capacity: int) -> List[str]:
        """Scale down GPU capacity to save costs"""
        
        # Find idle nodes (prioritize most expensive to terminate)
        idle_nodes = self.db.query(GPUNode).filter(
            GPUNode.status == 'available',
            GPUNode.current_project_id == None
        ).order_by(GPUNode.hourly_cost.desc()).limit(excess_capacity).all()
        
        terminated = []
        for node in idle_nodes:
            provider = self.providers[node.provider]
            if await provider.terminate_instance(node.instance_id):
                node.status = 'terminated'
                terminated.append(node.id)
                
        self.db.commit()
        return terminated
        
    async def assign_project_to_node(self, project_id: str, 
                                    duration_minutes: int) -> Optional[str]:
        """Assign project to best available GPU node"""
        
        # Calculate required GPU tier based on duration
        if duration_minutes <= 30:
            gpu_types = ['rtx4090', 'a100_40gb']
        elif duration_minutes <= 90:
            gpu_types = ['a100_40gb', 'a100_80gb']
        else:
            gpu_types = ['a100_80gb', 'h100']
            
        # Find best available node
        node = self.db.query(GPUNode).filter(
            GPUNode.status == 'available',
            GPUNode.gpu_type.in_(gpu_types)
        ).order_by(
            GPUNode.performance_score.desc(),
            GPUNode.hourly_cost.asc()
        ).first()
        
        if not node:
            # Try to scale up
            await self.scale_up(1)
            return None  # Will retry
            
        # Assign project
        node.status = 'busy'
        node.current_project_id = project_id
        self.db.commit()
        
        return node.id
        
    async def get_cluster_status(self) -> Dict:
        """Get current cluster status and metrics"""
        
        total_nodes = self.db.query(GPUNode).count()
        available = self.db.query(GPUNode).filter(GPUNode.status == 'available').count()
        busy = self.db.query(GPUNode).filter(GPUNode.status == 'busy').count()
        
        hourly_cost = self.db.query(GPUNode).filter(
            GPUNode.status.in_(['available', 'busy'])
        ).with_entities(
            GPUNode.hourly_cost
        ).all()
        
        total_hourly_cost = sum(cost[0] for cost in hourly_cost)
        
        return {
            'total_nodes': total_nodes,
            'available_nodes': available,
            'busy_nodes': busy,
            'utilization': (busy / total_nodes * 100) if total_nodes > 0 else 0,
            'hourly_cost': total_hourly_cost,
            'daily_cost': total_hourly_cost * 24,
            'monthly_cost': total_hourly_cost * 24 * 30
        }


# Provider implementations (simplified)
class RunPodProvider:
    """RunPod GPU provider interface"""
    
    async def launch_instances(self, count: int, gpu_type: str) -> List[Dict]:
        """Launch RunPod instances"""
        # This would use RunPod API
        # Simplified for example
        instances = []
        for i in range(count):
            instances.append({
                'instance_id': f"runpod_{secrets.token_hex(8)}",
                'gpu_type': gpu_type,
                'hourly_cost': 0.44 if gpu_type == 'rtx4090' else 1.19,
                'region': 'us-east-1'
            })
        return instances
        
    async def terminate_instance(self, instance_id: str) -> bool:
        """Terminate RunPod instance"""
        # Would call RunPod API
        return True

class VastAIProvider:
    """Vast.ai GPU provider interface"""
    
    async def launch_instances(self, count: int, gpu_type: str) -> List[Dict]:
        """Launch Vast.ai instances"""
        instances = []
        for i in range(count):
            instances.append({
                'instance_id': f"vast_{secrets.token_hex(8)}",
                'gpu_type': gpu_type,
                'hourly_cost': 0.35 if gpu_type == 'rtx4090' else 0.99,
                'region': 'us-west-2'
            })
        return instances
        
    async def terminate_instance(self, instance_id: str) -> bool:
        return True

class LambdaLabsProvider:
    """Lambda Labs GPU provider interface"""
    
    async def launch_instances(self, count: int, gpu_type: str) -> List[Dict]:
        """Launch Lambda Labs instances"""
        instances = []
        for i in range(count):
            instances.append({
                'instance_id': f"lambda_{secrets.token_hex(8)}",
                'gpu_type': gpu_type,
                'hourly_cost': 0.50 if gpu_type == 'rtx4090' else 1.49,
                'region': 'us-central-1'
            })
        return instances
        
    async def terminate_instance(self, instance_id: str) -> bool:
        return True


# FastAPI application
app = FastAPI(title="SkyReels Film Platform API")

# Dependency injection
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

auth_service = AuthenticationService()

# API Models
class UserRegistration(BaseModel):
    email: EmailStr
    password: str
    referral_code: Optional[str] = None
    
class ProjectRequest(BaseModel):
    title: str
    duration_minutes: int
    format: str = "film"
    include_script: bool = True
    include_storyboard: bool = True
    quality: str = "standard"
    source_content: Optional[str] = None

# API Endpoints
@app.post("/api/register")
async def register(registration: UserRegistration, db: Session = Depends(get_db)):
    """Register new user"""
    
    # Check if email exists
    existing = db.query(User).filter(User.email == registration.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Create user
    user = User(
        id=secrets.token_hex(16),
        email=registration.email,
        password_hash=auth_service.hash_password(registration.password),
        referral_code=secrets.token_hex(8),
        referred_by=registration.referral_code,
        api_key=secrets.token_hex(32)
    )
    
    # Give bonus credits for referral
    if registration.referral_code:
        referrer = db.query(User).filter(User.referral_code == registration.referral_code).first()
        if referrer:
            referrer.credits += 25  # Bonus credits for referral
            user.credits = 10  # Bonus for being referred
            
    db.add(user)
    db.commit()
    
    token = auth_service.create_access_token(user.id)
    
    return {
        "user_id": user.id,
        "email": user.email,
        "token": token,
        "api_key": user.api_key,
        "credits": user.credits
    }

@app.post("/api/projects")
async def create_project(
    project: ProjectRequest,
    authorization: HTTPAuthorizationCredentials = Depends(auth_service.security),
    db: Session = Depends(get_db)
):
    """Create new film project"""
    
    # Verify token
    payload = auth_service.verify_token(authorization.credentials)
    user_id = payload['user_id']
    
    # Check credits
    user = db.query(User).filter(User.id == user_id).first()
    tier_info = PlatformConfig.SUBSCRIPTION_TIERS[user.subscription_tier]
    
    # Check duration limit
    if tier_info['max_duration_minutes'] > 0 and project.duration_minutes > tier_info['max_duration_minutes']:
        raise HTTPException(status_code=403, 
                          detail=f"Duration exceeds tier limit of {tier_info['max_duration_minutes']} minutes")
    
    # Calculate cost
    from skyreels_film_platform import PricingEngine
    costs = PricingEngine.calculate_project_cost(
        duration_minutes=project.duration_minutes,
        include_script=project.include_script,
        include_storyboard=project.include_storyboard,
        quality=project.quality
    )
    
    if user.credits < costs['total']:
        raise HTTPException(status_code=402, 
                          detail=f"Insufficient credits. Need {costs['total']}, have {user.credits}")
    
    # Create project
    project_obj = Project(
        id=secrets.token_hex(16),
        user_id=user_id,
        title=project.title,
        duration_minutes=project.duration_minutes,
        format=project.format,
        status='queued',
        cost=costs['total'],
        metadata=json.dumps(project.dict())
    )
    
    db.add(project_obj)
    
    # Deduct credits
    credit_manager = CreditManager(db)
    await credit_manager.use_credits(user_id, project_obj.id, project.duration_minutes)
    
    # Assign to GPU node
    orchestrator = GPUOrchestrator(db)
    node_id = await orchestrator.assign_project_to_node(
        project_obj.id, 
        project.duration_minutes
    )
    
    db.commit()
    
    return {
        "project_id": project_obj.id,
        "status": "queued",
        "estimated_completion": (datetime.utcnow() + 
                                timedelta(minutes=project.duration_minutes * 2)).isoformat(),
        "cost": costs['total'],
        "assigned_node": node_id
    }

@app.get("/api/cluster/status")
async def get_cluster_status(db: Session = Depends(get_db)):
    """Get GPU cluster status"""
    orchestrator = GPUOrchestrator(db)
    return await orchestrator.get_cluster_status()

@app.post("/api/cluster/scale")
async def scale_cluster(
    action: str,
    count: int,
    authorization: HTTPAuthorizationCredentials = Depends(auth_service.security),
    db: Session = Depends(get_db)
):
    """Manually scale cluster (admin only)"""
    
    # Verify admin token
    payload = auth_service.verify_token(authorization.credentials)
    user = db.query(User).filter(User.id == payload['user_id']).first()
    
    if user.subscription_tier != 'enterprise':  # Only enterprise can scale
        raise HTTPException(status_code=403, detail="Admin access required")
    
    orchestrator = GPUOrchestrator(db)
    
    if action == "up":
        nodes = await orchestrator.scale_up(count)
        return {"action": "scale_up", "nodes_added": nodes}
    elif action == "down":
        nodes = await orchestrator.scale_down(count)
        return {"action": "scale_down", "nodes_removed": nodes}
    else:
        raise HTTPException(status_code=400, detail="Invalid action")


# Database initialization
engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///skyreels_platform.db"))
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("SKYREELS MONETIZATION PLATFORM")
    print("=" * 60)
    print("\n💰 Pricing:")
    print("  Script: $1/minute")
    print("  Video: $3/minute")
    print("  60-min film: ~$240 revenue")
    print("  GPU cost: ~$5-10")
    print("  Profit margin: 95%+")
    print("\n🚀 Starting API server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)