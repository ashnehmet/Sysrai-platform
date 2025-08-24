"""
Basic tests for Sysrai Platform
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import get_db, Base
from models import User

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test database
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_register_user():
    """Test user registration"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_register_duplicate_email():
    """Test registering with duplicate email"""
    # Register first user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "password123"
        }
    )
    
    # Try to register again with same email
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "password456"
        }
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

def test_login():
    """Test user login"""
    # Register user first
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "loginpassword"
        }
    )
    
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "loginpassword"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

def test_invalid_login():
    """Test login with invalid credentials"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401

def test_protected_endpoint_without_auth():
    """Test accessing protected endpoint without authentication"""
    response = client.get("/api/v1/credits/balance")
    assert response.status_code == 401

def test_protected_endpoint_with_auth():
    """Test accessing protected endpoint with authentication"""
    # Register and get token
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "protected@example.com",
            "password": "protectedpassword"
        }
    )
    token = response.json()["access_token"]
    
    # Access protected endpoint
    response = client.get(
        "/api/v1/credits/balance",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "credits" in data

@pytest.fixture
def authenticated_user():
    """Fixture to create and return authenticated user"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "fixture@example.com",
            "password": "fixturepassword"
        }
    )
    return response.json()

def test_create_project_insufficient_credits(authenticated_user):
    """Test creating project with insufficient credits"""
    token = authenticated_user["access_token"]
    
    response = client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test Film",
            "duration_minutes": 60,  # Costs more than free credits
            "format": "film",
            "source_content": "A test film about AI"
        }
    )
    assert response.status_code == 402
    assert "Insufficient credits" in response.json()["detail"]

def test_list_projects_empty(authenticated_user):
    """Test listing projects for new user"""
    token = authenticated_user["access_token"]
    
    response = client.get(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json() == []