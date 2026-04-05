"""
Pytest configuration and shared fixtures.

Sets up a test database (in-memory SQLite) and provides
a FastAPI TestClient preconfigured with dependency overrides.
This ensures tests are isolated and don't affect the development database.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

# ─── Test Database Setup ─────────────────────────────────────────

TEST_DATABASE_URL = "sqlite:///./test_finance.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Test database session that rolls back after each test."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the database dependency for all tests
app.dependency_overrides[get_db] = override_get_db


# ─── Fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once before the test session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()  # Release all connections before file delete
    # Clean up test database file
    import os
    try:
        if os.path.exists("test_finance.db"):
            os.remove("test_finance.db")
    except PermissionError:
        pass  # Windows file locking — file will be cleaned on next run


@pytest.fixture(scope="session")
def client():
    """Provide a TestClient for the entire test session."""
    return TestClient(app)


@pytest.fixture(scope="session")
def admin_token(client):
    """Register and login an admin user, return the JWT token."""
    # Register
    client.post("/api/v1/auth/register", json={
        "name": "Test Admin",
        "email": "testadmin@example.com",
        "password": "admin123",
        "role": "admin",
    })
    # Login
    response = client.post("/api/v1/auth/login", json={
        "email": "testadmin@example.com",
        "password": "admin123",
    })
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def viewer_token(client):
    """Register and login a viewer user, return the JWT token."""
    client.post("/api/v1/auth/register", json={
        "name": "Test Viewer",
        "email": "testviewer@example.com",
        "password": "viewer123",
        "role": "viewer",
    })
    response = client.post("/api/v1/auth/login", json={
        "email": "testviewer@example.com",
        "password": "viewer123",
    })
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def analyst_token(client):
    """Register and login an analyst user, return the JWT token."""
    client.post("/api/v1/auth/register", json={
        "name": "Test Analyst",
        "email": "testanalyst@example.com",
        "password": "analyst123",
        "role": "analyst",
    })
    response = client.post("/api/v1/auth/login", json={
        "email": "testanalyst@example.com",
        "password": "analyst123",
    })
    return response.json()["access_token"]


def auth_header(token: str) -> dict:
    """Helper to create an Authorization header."""
    return {"Authorization": f"Bearer {token}"}
