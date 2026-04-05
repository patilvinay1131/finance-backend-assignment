"""
Tests for authentication endpoints.

Covers: registration, login, profile, input validation, and error handling.
"""

from tests.conftest import auth_header


class TestRegistration:
    """Tests for POST /api/v1/auth/register"""

    def test_register_success(self, client):
        response = client.post("/api/v1/auth/register", json={
            "name": "New User",
            "email": "newuser@test.com",
            "password": "password123",
            "role": "viewer",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["role"] == "viewer"
        assert data["is_active"] is True
        assert "hashed_password" not in data  # Password must never be in response

    def test_register_duplicate_email(self, client):
        # First registration
        client.post("/api/v1/auth/register", json={
            "name": "Dup User",
            "email": "duplicate@test.com",
            "password": "pass123456",
            "role": "viewer",
        })
        # Second registration with same email
        response = client.post("/api/v1/auth/register", json={
            "name": "Dup User 2",
            "email": "duplicate@test.com",
            "password": "pass654321",
            "role": "viewer",
        })
        assert response.status_code == 409

    def test_register_invalid_email(self, client):
        response = client.post("/api/v1/auth/register", json={
            "name": "Bad Email",
            "email": "not-an-email",
            "password": "pass123456",
            "role": "viewer",
        })
        assert response.status_code == 422

    def test_register_short_password(self, client):
        response = client.post("/api/v1/auth/register", json={
            "name": "Short Pass",
            "email": "shortpass@test.com",
            "password": "abc",
            "role": "viewer",
        })
        assert response.status_code == 422

    def test_register_invalid_role(self, client):
        response = client.post("/api/v1/auth/register", json={
            "name": "Bad Role",
            "email": "badrole@test.com",
            "password": "pass123456",
            "role": "superadmin",
        })
        assert response.status_code == 422

    def test_register_blank_name(self, client):
        response = client.post("/api/v1/auth/register", json={
            "name": "   ",
            "email": "blankname@test.com",
            "password": "pass123456",
            "role": "viewer",
        })
        assert response.status_code == 422

    def test_register_missing_fields(self, client):
        response = client.post("/api/v1/auth/register", json={
            "name": "No Email",
        })
        assert response.status_code == 422


class TestLogin:
    """Tests for POST /api/v1/auth/login"""

    def test_login_success(self, client, admin_token):
        response = client.post("/api/v1/auth/login", json={
            "email": "testadmin@example.com",
            "password": "admin123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["role"] == "admin"

    def test_login_wrong_password(self, client):
        response = client.post("/api/v1/auth/login", json={
            "email": "testadmin@example.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_login_nonexistent_email(self, client):
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "anything",
        })
        assert response.status_code == 401


class TestProfile:
    """Tests for GET /api/v1/auth/me"""

    def test_get_profile(self, client, admin_token):
        response = client.get("/api/v1/auth/me", headers=auth_header(admin_token))
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testadmin@example.com"
        assert data["role"] == "admin"

    def test_get_profile_no_auth(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 403  # HTTPBearer returns 403 when no creds

    def test_get_profile_invalid_token(self, client):
        response = client.get("/api/v1/auth/me",
                              headers={"Authorization": "Bearer invalid-token"})
        assert response.status_code == 401
