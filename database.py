"""
Database configuration for Sysrai Platform
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sysrai.db")

# Handle PostgreSQL vs SQLite connection
if DATABASE_URL.startswith("postgresql://"):
    # PostgreSQL requires psycopg2 driver specification
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")

# SQLAlchemy setup with connection pooling for production
if "sqlite" in DATABASE_URL:
    # SQLite doesn't support connection pooling well
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL with connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=40,
        pool_pre_ping=True,
        pool_recycle=3600
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()