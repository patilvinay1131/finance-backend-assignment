"""
Finance Data Processing & Access Control Backend

Main application entry point. Sets up:
    - FastAPI application with OpenAPI metadata
    - CORS middleware for frontend consumption
    - Global exception handlers for consistent error responses
    - All API route routers
    - Database table creation on startup
    - Default admin user seeding

Architecture:
    Routes → Services → Models/Database
    Routes handle HTTP concerns, services contain business logic,
    models define the data schema, and utils provide cross-cutting concerns.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config
from app.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.finance import FinanceRecord
from app.utils.security import hash_password

from app.routes import auth_routes, user_routes, finance_routes, dashboard_routes

# ─── Logging ─────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Startup / Shutdown Lifespan ─────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on application startup and shutdown.
    - Creates database tables if they don't exist
    - Seeds a default admin user for immediate testing
    """
    # Startup
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    # Seed default admin user
    db = SessionLocal()
    try:
        existing_admin = (
            db.query(User)
            .filter(User.email == config.DEFAULT_ADMIN_EMAIL)
            .first()
        )
        if not existing_admin:
            admin = User(
                name=config.DEFAULT_ADMIN_NAME,
                email=config.DEFAULT_ADMIN_EMAIL,
                hashed_password=hash_password(config.DEFAULT_ADMIN_PASSWORD),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info(
                f"Default admin user created: {config.DEFAULT_ADMIN_EMAIL} / "
                f"{config.DEFAULT_ADMIN_PASSWORD}"
            )
        else:
            logger.info("Default admin user already exists")
    finally:
        db.close()

    yield

    # Shutdown
    logger.info("Application shutting down")


# ─── Application ────────────────────────────────────────────────

app = FastAPI(
    title="Finance Data Processing and Access Control Backend",
    description=(
        "A backend API for a finance dashboard system with role-based access control.\n\n"
        "**Features:**\n"
        "- JWT authentication with bcrypt password hashing\n"
        "- Role-based access control (Viewer / Analyst / Admin)\n"
        "- Financial record CRUD with filtering and pagination\n"
        "- Dashboard analytics (summary, category breakdown, trends)\n"
        "- Soft delete for audit trail preservation\n\n"
        "**Architecture:** Routes → Services → Models (separation of concerns)"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ─── CORS Middleware ─────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Global Exception Handlers ──────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom handler for Pydantic validation errors.
    Returns a clean, structured error response instead of raw Pydantic output.
    """
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation failed",
            "errors": errors,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Consistent format for all HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all for unexpected errors. Prevents stack traces from leaking to clients."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred",
            "status_code": 500,
        },
    )


# ─── Register Routers ───────────────────────────────────────────

app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(finance_routes.router)
app.include_router(dashboard_routes.router)


# ─── Health Check ────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    """Root endpoint — confirms the API is running."""
    return {
        "status": "healthy",
        "service": "Finance Data Processing and Access Control Backend",
        "version": "1.0.0",
        "docs": "/docs",
    }
