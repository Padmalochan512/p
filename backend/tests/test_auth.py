import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_demo_user_login():
    response = client.post("/api/auth/login", json={
        "email": "demo@antigravity.ai",
        "password": "demo1234"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "demo@antigravity.ai"

def test_register_new_user():
    import uuid
    random_email = f"user_{uuid.uuid4().hex[:6]}@test.com"
    response = client.post("/api/auth/register", json={
        "email": random_email,
        "password": "password123",
        "full_name": "Test User",
        "default_currency": "INR"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == random_email
