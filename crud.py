"""
CRUD operations for Sysrai Platform
"""

import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
import stripe

from models import User, Project, Transaction
import schemas
from pricing import CREDIT_PACKAGES

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = "your-secret-key-here"  # Use env variable in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Stripe setup
stripe.api_key = "your-stripe-key"  # Use env variable in production

# User operations
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user_data: schemas.UserCreate):
    user = User(
        id=secrets.token_hex(16),
        email=user_data.email,
        password_hash=pwd_context.hash(user_data.password),
        credits=10.0  # Free credits on signup
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user or not pwd_context.verify(password, user.password_hash):
        return None
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    return user

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Project operations
def create_project(db: Session, project_data: schemas.ProjectCreate, user_id: str, cost: float):
    project = Project(
        id=secrets.token_hex(16),
        user_id=user_id,
        title=project_data.title,
        duration_minutes=project_data.duration_minutes,
        format=project_data.format,
        status="queued",
        cost=cost,
        estimated_completion=datetime.utcnow() + timedelta(minutes=project_data.duration_minutes * 2),
        metadata=project_data.json()
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

def get_project(db: Session, project_id: str):
    return db.query(Project).filter(Project.id == project_id).first()

def get_user_projects(db: Session, user_id: str, skip: int = 0, limit: int = 100):
    return db.query(Project).filter(
        Project.user_id == user_id
    ).offset(skip).limit(limit).all()

def update_project_status(db: Session, project_id: str, status: str, progress: int):
    project = get_project(db, project_id)
    if project:
        project.status = status
        project.progress = progress
        db.commit()

def complete_project(db: Session, project_id: str, film_url: str):
    project = get_project(db, project_id)
    if project:
        project.status = "complete"
        project.progress = 100
        project.film_url = film_url
        project.completed_at = datetime.utcnow()
        db.commit()

def fail_project(db: Session, project_id: str, error: str):
    project = get_project(db, project_id)
    if project:
        project.status = "failed"
        project.metadata = f"{project.metadata}\nError: {error}"
        db.commit()

# Credit operations
def use_credits(db: Session, user_id: str, amount: float, description: str):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.credits -= amount
        
        # Record transaction
        transaction = Transaction(
            id=secrets.token_hex(16),
            user_id=user_id,
            type="usage",
            amount=-amount,
            credits=-amount,
            description=description
        )
        db.add(transaction)
        db.commit()

def add_credits(db: Session, user_id: str, amount: float, description: str, payment_id: str = None):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.credits += amount
        
        # Record transaction
        transaction = Transaction(
            id=secrets.token_hex(16),
            user_id=user_id,
            type="purchase",
            amount=amount,
            credits=amount,
            description=description,
            stripe_payment_id=payment_id
        )
        db.add(transaction)
        db.commit()

# Payment operations
def create_payment_intent(package_type: str):
    package = CREDIT_PACKAGES.get(package_type)
    if not package:
        raise ValueError("Invalid package type")
    
    return stripe.PaymentIntent.create(
        amount=int(package["price"] * 100),  # Convert to cents
        currency="usd",
        metadata={
            "package_type": package_type,
            "credits": package["credits"] + package["bonus"]
        }
    )