"""
Sysrai Platform - Main Application
Deployed on Digital Ocean, uses RunPod for GPU processing
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import get_db, engine, Base
from auth import get_current_user
from models import User, Project, Transaction
from runpod_api import RunPodClient
from pricing import calculate_project_cost
import schemas
import crud

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize RunPod client
runpod_client = RunPodClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle"""
    # Startup
    print("🚀 Starting Sysrai Platform...")
    yield
    # Shutdown - ensure RunPod is stopped
    print("🛑 Shutting down...")
    await runpod_client.stop_pod()

# Create FastAPI app
app = FastAPI(
    title="Sysrai AI Film Platform",
    description="Create full-length films with AI for $250",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "sysrai-platform",
        "version": "1.0.0"
    }

# Authentication endpoints
@app.post("/api/v1/auth/register", response_model=schemas.Token)
async def register(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """Register new user"""
    
    # Check if email exists
    if crud.get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = crud.create_user(db, user_data)
    
    # Generate token
    access_token = crud.create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "credits": user.credits
    }

@app.post("/api/v1/auth/login", response_model=schemas.Token)
async def login(
    form_data: schemas.UserLogin,
    db: Session = Depends(get_db)
):
    """Login user"""
    
    user = crud.authenticate_user(db, form_data.email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )
    
    access_token = crud.create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "credits": user.credits
    }

# Project endpoints
@app.post("/api/v1/projects", response_model=schemas.ProjectResponse)
async def create_project(
    project_data: schemas.ProjectCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new film project"""
    
    # Calculate cost
    cost = calculate_project_cost(
        duration_minutes=project_data.duration_minutes,
        include_script=project_data.include_script,
        include_storyboard=project_data.include_storyboard,
        quality=project_data.quality
    )
    
    # Check credits
    if current_user.credits < cost["total"]:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need {cost['total']}, have {current_user.credits}"
        )
    
    # Create project
    project = crud.create_project(db, project_data, current_user.id, cost["total"])
    
    # Deduct credits
    crud.use_credits(db, current_user.id, cost["total"], f"Project: {project.title}")
    
    # Start generation in background
    background_tasks.add_task(
        generate_film_async,
        project.id,
        project_data.dict(),
        db
    )
    
    return {
        "project_id": project.id,
        "title": project.title,
        "status": project.status,
        "cost": cost["total"],
        "estimated_completion": project.estimated_completion
    }

@app.get("/api/v1/projects/{project_id}", response_model=schemas.ProjectStatus)
async def get_project_status(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project status"""
    
    project = crud.get_project(db, project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "project_id": project.id,
        "title": project.title,
        "status": project.status,
        "progress": project.progress,
        "film_url": project.film_url,
        "created_at": project.created_at,
        "completed_at": project.completed_at
    }

@app.get("/api/v1/projects", response_model=List[schemas.ProjectSummary])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's projects"""
    
    projects = crud.get_user_projects(db, current_user.id, skip, limit)
    
    return projects

# Credits and billing
@app.post("/api/v1/credits/purchase")
async def purchase_credits(
    package: schemas.CreditPackage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Purchase credits"""
    
    # Create Stripe payment intent
    payment_intent = crud.create_payment_intent(package.package_type)
    
    return {
        "payment_intent_id": payment_intent.id,
        "client_secret": payment_intent.client_secret,
        "amount": payment_intent.amount / 100,
        "credits": package.credits
    }

@app.get("/api/v1/credits/balance")
async def get_credit_balance(
    current_user: User = Depends(get_current_user)
):
    """Get current credit balance"""
    
    return {
        "user_id": current_user.id,
        "credits": current_user.credits,
        "subscription_tier": current_user.subscription_tier
    }

# RunPod management (admin only)
@app.get("/api/v1/admin/runpod/status")
async def get_runpod_status(
    current_user: User = Depends(get_current_user)
):
    """Get RunPod instance status (admin only)"""
    
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    status = await runpod_client.get_pod_status()
    
    return status

@app.post("/api/v1/admin/runpod/stop")
async def stop_runpod(
    current_user: User = Depends(get_current_user)
):
    """Stop RunPod instance to save costs (admin only)"""
    
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await runpod_client.stop_pod()
    
    return result

# Background task for film generation
async def generate_film_async(project_id: str, project_data: dict, db: Session):
    """Generate film in background"""
    
    try:
        # Update status
        crud.update_project_status(db, project_id, "generating", 10)
        
        # Generate script if needed
        if project_data.get("include_script"):
            script = await generate_script(project_data["source_content"])
            crud.update_project_status(db, project_id, "script_complete", 30)
        
        # Generate storyboard if needed
        if project_data.get("include_storyboard"):
            storyboard = await generate_storyboard(script)
            crud.update_project_status(db, project_id, "storyboard_complete", 50)
        
        # Generate video with RunPod
        film_result = await runpod_client.generate_film(
            storyboard,
            project_data["title"]
        )
        
        if film_result["success"]:
            # Upload to Digital Ocean Spaces
            film_url = await upload_to_spaces(film_result["film_url"])
            
            # Update project
            crud.complete_project(db, project_id, film_url)
        else:
            crud.fail_project(db, project_id, film_result["error"])
            
    except Exception as e:
        crud.fail_project(db, project_id, str(e))

# Script and video generation functions
async def generate_script(source_content: str, duration_minutes: int = 30) -> dict:
    """Generate film script from source content"""
    from script_generator import ScriptGenerator
    from config import get_settings
    
    settings = get_settings()
    generator = ScriptGenerator(os.getenv("OPENAI_API_KEY"))
    
    try:
        script = await generator.generate_film_script(
            source_content=source_content,
            duration_minutes=duration_minutes,
            genre="drama",
            style="cinematic"
        )
        return script.dict()
    except Exception as e:
        raise Exception(f"Script generation failed: {e}")

async def generate_storyboard(script: dict) -> list:
    """Generate storyboard from script"""
    from script_generator import StoryboardGenerator, ScriptGenerator, FilmScript
    
    script_gen = ScriptGenerator(os.getenv("OPENAI_API_KEY"))
    storyboard_gen = StoryboardGenerator(script_gen)
    
    try:
        film_script = FilmScript(**script)
        storyboard = storyboard_gen.create_storyboard(film_script)
        return storyboard
    except Exception as e:
        raise Exception(f"Storyboard generation failed: {e}")

async def upload_to_spaces(file_url: str) -> str:
    """Upload file to Digital Ocean Spaces"""
    import boto3
    import httpx
    from datetime import datetime
    
    try:
        # Initialize S3 client for Digital Ocean Spaces
        s3_client = boto3.client(
            's3',
            region_name=os.getenv("DO_SPACES_REGION", "nyc3"),
            endpoint_url=os.getenv("DO_SPACES_ENDPOINT", "https://nyc3.digitaloceanspaces.com"),
            aws_access_key_id=os.getenv("DO_SPACES_KEY"),
            aws_secret_access_key=os.getenv("DO_SPACES_SECRET")
        )
        
        # Download file from RunPod
        async with httpx.AsyncClient() as client:
            response = await client.get(file_url)
            response.raise_for_status()
            
            # Generate unique filename
            filename = f"films/{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            
            # Upload to Spaces
            s3_client.put_object(
                Bucket=os.getenv("DO_SPACES_BUCKET", "sysrai-videos"),
                Key=filename,
                Body=response.content,
                ContentType='video/mp4',
                ACL='public-read'
            )
            
            # Return public URL
            bucket = os.getenv("DO_SPACES_BUCKET", "sysrai-videos")
            endpoint = os.getenv("DO_SPACES_ENDPOINT", "https://nyc3.digitaloceanspaces.com")
            public_url = f"{endpoint}/{bucket}/{filename}"
            return public_url
            
    except Exception as e:
        raise Exception(f"File upload failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)