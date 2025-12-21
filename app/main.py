"""
Snake Classic Backend API - Main Application
"""
import logging
import os
import sys
import traceback
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

from .core.config import settings
from .database import init_db
from .api.v1 import api_router
from .routes import notifications, test, purchases, battle_pass
from .services.scheduler_service import scheduler_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("=" * 70)
    print("[STARTUP] Starting Snake Classic Backend API...")
    print("=" * 70)

    try:
        # Initialize database
        print(f"[DATABASE] {settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}")
        init_db()
        print("[OK] Database initialized successfully")

        # Seed default achievements
        from .database import SessionLocal
        from .services.achievement_service import achievement_service
        db = SessionLocal()
        try:
            created = achievement_service.seed_achievements(db)
            if created > 0:
                print(f"[OK] Seeded {created} new achievements")
            else:
                print("[OK] Achievements already seeded")
        finally:
            db.close()

        # Start the scheduler service
        scheduler_service.start()
        print("[OK] Scheduler service started")

        print(f"[DEBUG] Debug mode: {settings.DEBUG}")
        print("=" * 70)
        print(f"[API] Running at: http://{settings.API_HOST}:{settings.API_PORT}")
        print(f"[DOCS] API Docs: http://{settings.API_HOST}:{settings.API_PORT}/docs")
        print("=" * 70)

    except Exception as e:
        logger.error(f"Failed to initialize backend: {e}")
        print(f"[ERROR] Failed to initialize backend: {e}")
        raise

    yield  # Application runs here

    # Shutdown
    print("[SHUTDOWN] Shutting down Snake Classic Backend API...")

    try:
        # Stop the scheduler service
        scheduler_service.shutdown()
        print("[OK] Scheduler service stopped")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Snake Classic game backend with PostgreSQL, authentication, leaderboards, and more",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
    redirect_slashes=False
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unexpected errors."""
    # Generate a unique error ID for tracking
    error_id = str(uuid.uuid4())[:8]

    # Always log the full error on the server
    logger.error(
        f"[ERROR_ID: {error_id}] Unhandled exception on {request.method} {request.url.path}",
        exc_info=True
    )

    if settings.DEBUG:
        # Development: return detailed error for debugging
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "detail": str(exc),
                "error_id": error_id,
                "type": type(exc).__name__,
                "path": str(request.url.path),
                "traceback": traceback.format_exc()
            }
        )
    else:
        # Production: return generic error, hide internal details
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "detail": "An internal server error occurred. Please try again later.",
                "error_id": error_id
            }
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs" if settings.DEBUG else "disabled",
        "features": [
            "Firebase Auth + Google Sign-In",
            "PostgreSQL database",
            "JWT authentication",
            "Leaderboards & scores",
            "Achievements system",
            "Social features",
            "Tournaments",
            "Multiplayer with WebSocket",
            "Battle Pass",
            "In-app purchases",
            "Push notifications (FCM)"
        ]
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    from app.utils.time_utils import to_utc_isoformat, utc_now

    try:
        # Check scheduler status
        scheduler_running = scheduler_service.scheduler.running if scheduler_service.scheduler else False

        # Get scheduled jobs count
        scheduled_jobs = len(scheduler_service.get_scheduled_jobs()) if scheduler_service.scheduler else 0

        return {
            "status": "healthy",
            "timestamp": to_utc_isoformat(utc_now()),
            "service": "snake-classic-api",
            "version": "1.0.0",
            "services": {
                "database": {
                    "status": "connected",
                    "host": settings.DATABASE_HOST
                },
                "scheduler": {
                    "status": "running" if scheduler_running else "stopped",
                    "scheduled_jobs": scheduled_jobs
                },
                "firebase": {
                    "status": "connected",
                    "project_id": settings.FIREBASE_PROJECT_ID
                }
            }
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Include API router (new structure with auth, users, etc.)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Include legacy routers (will be migrated later)
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(test.router, prefix="/api/v1")
app.include_router(purchases.router, prefix="/api/v1")
app.include_router(battle_pass.router, prefix="/api/v1")


# Tournament management endpoints
@app.post("/api/v1/tournaments/schedule-notifications")
async def schedule_tournament_notifications(
    tournament_name: str,
    tournament_id: str,
    start_time: str,  # ISO format datetime string
    reminder_minutes: list = [60, 15, 5]
):
    """Schedule all notifications for a tournament."""
    try:
        from datetime import datetime
        
        # Parse the start time
        start_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        
        # Schedule the notifications
        job_ids = await scheduler_service.schedule_tournament_notifications(
            tournament_name=tournament_name,
            tournament_id=tournament_id,
            start_time=start_datetime,
            reminder_times=reminder_minutes
        )
        
        return {
            "success": True,
            "message": f"Scheduled {len(job_ids)} notifications for tournament '{tournament_name}'",
            "job_ids": job_ids,
            "tournament_name": tournament_name,
            "tournament_id": tournament_id,
            "start_time": start_time
        }
    
    except Exception as e:
        logger.error(f"Failed to schedule tournament notifications: {e}")
        return {
            "success": False,
            "message": f"Failed to schedule tournament notifications: {str(e)}",
            "error": str(e)
        }


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )