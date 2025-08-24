"""
Database models for Sysrai Platform
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    credits = Column(Float, default=10.0)
    subscription_tier = Column(String, default="free")
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    projects = relationship("Project", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    title = Column(String)
    duration_minutes = Column(Integer)
    format = Column(String)  # film, series, short
    status = Column(String)  # queued, generating, complete, failed
    progress = Column(Integer, default=0)
    cost = Column(Float)
    film_url = Column(String, nullable=True)
    metadata = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    estimated_completion = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="projects")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    type = Column(String)  # purchase, usage, refund
    amount = Column(Float)
    credits = Column(Float)
    description = Column(String)
    stripe_payment_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="transactions")