"""
Pydantic schemas for API validation
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    credits: float

# Project schemas
class ProjectCreate(BaseModel):
    title: str
    duration_minutes: int
    format: str = "film"
    include_script: bool = True
    include_storyboard: bool = True
    quality: str = "standard"
    source_content: Optional[str] = None

class ProjectResponse(BaseModel):
    project_id: str
    title: str
    status: str
    cost: float
    estimated_completion: datetime

class ProjectStatus(BaseModel):
    project_id: str
    title: str
    status: str
    progress: int
    film_url: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

class ProjectSummary(BaseModel):
    id: str
    title: str
    duration_minutes: int
    status: str
    created_at: datetime

# Credit schemas
class CreditPackage(BaseModel):
    package_type: str  # small, medium, large, mega
    credits: int