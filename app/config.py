"""
Application configuration — centralized settings management.

Loads configuration from environment variables with sensible defaults.
In production, set these via .env file or system environment variables.

Design Decision:
    Using a simple module-level approach rather than Pydantic Settings
    to keep dependencies minimal while still externalizing all configuration.
"""

import os


# ─── Database ────────────────────────────────────────────────────────

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./finance.db")

# ─── Security / JWT ──────────────────────────────────────────────────

SECRET_KEY: str = os.getenv("SECRET_KEY", "finance-dev-secret-change-in-production")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "24"))

# ─── Default Admin Seed ──────────────────────────────────────────────

DEFAULT_ADMIN_EMAIL: str = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@finance.com")
DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_NAME: str = os.getenv("DEFAULT_ADMIN_NAME", "System Admin")

# ─── CORS ────────────────────────────────────────────────────────────

# Comma-separated origins, e.g. "http://localhost:3000,https://app.example.com"
_cors_origins = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS: list[str] = (
    ["*"] if _cors_origins == "*" else [o.strip() for o in _cors_origins.split(",")]
)

# ─── Pagination Defaults ─────────────────────────────────────────────

DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "10"))
MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "100"))
