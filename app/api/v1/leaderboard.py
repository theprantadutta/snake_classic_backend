"""
Leaderboard API endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.score import LeaderboardResponse
from app.services.leaderboard_service import leaderboard_service

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/global", response_model=LeaderboardResponse)
async def get_global_leaderboard(
    game_mode: str = Query("classic", description="Game mode"),
    difficulty: str = Query("normal", description="Difficulty level"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get global all-time leaderboard"""
    return leaderboard_service.get_global_leaderboard(
        db, game_mode, difficulty, page, page_size, current_user.id
    )


@router.get("/weekly", response_model=LeaderboardResponse)
async def get_weekly_leaderboard(
    game_mode: str = Query("classic", description="Game mode"),
    difficulty: str = Query("normal", description="Difficulty level"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get weekly leaderboard (scores from last 7 days)"""
    return leaderboard_service.get_weekly_leaderboard(
        db, game_mode, difficulty, page, page_size, current_user.id
    )


@router.get("/daily", response_model=LeaderboardResponse)
async def get_daily_leaderboard(
    game_mode: str = Query("classic", description="Game mode"),
    difficulty: str = Query("normal", description="Difficulty level"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get daily leaderboard (scores from today)"""
    return leaderboard_service.get_daily_leaderboard(
        db, game_mode, difficulty, page, page_size, current_user.id
    )


@router.get("/friends", response_model=LeaderboardResponse)
async def get_friends_leaderboard(
    game_mode: str = Query("classic", description="Game mode"),
    difficulty: str = Query("normal", description="Difficulty level"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get friends leaderboard (you and your friends)"""
    return leaderboard_service.get_friends_leaderboard(
        db, current_user.id, game_mode, difficulty, page, page_size
    )
