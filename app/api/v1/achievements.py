"""
Achievements API endpoints
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.achievement import (
    AchievementResponse,
    UserAchievementSummary,
    AchievementProgressUpdate,
    AchievementProgressResponse,
    ClaimRewardRequest,
    ClaimRewardResponse,
)
from app.services.achievement_service import achievement_service

router = APIRouter(prefix="/achievements", tags=["achievements"])


@router.get("", response_model=List[AchievementResponse])
async def get_all_achievements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all available achievements"""
    achievements = achievement_service.get_all_achievements(db)
    return [AchievementResponse.model_validate(a) for a in achievements]


@router.get("/me", response_model=UserAchievementSummary)
async def get_my_achievements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's achievement progress"""
    return achievement_service.get_user_achievement_summary(db, current_user.id)


@router.get("/user/{user_id}", response_model=UserAchievementSummary)
async def get_user_achievements(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get another user's achievement progress"""
    return achievement_service.get_user_achievement_summary(db, user_id)


@router.post("/progress", response_model=AchievementProgressResponse)
async def update_achievement_progress(
    progress_update: AchievementProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update progress for an achievement"""
    try:
        return achievement_service.update_progress(
            db,
            current_user.id,
            progress_update.achievement_id,
            progress_update.progress_increment
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/claim", response_model=ClaimRewardResponse)
async def claim_achievement_reward(
    claim_request: ClaimRewardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Claim reward for an unlocked achievement"""
    # Get achievement
    achievement = achievement_service.get_achievement_by_id(db, claim_request.achievement_id)
    if not achievement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Achievement not found"
        )

    # Check if user has unlocked it
    from app.models.achievement import UserAchievement
    user_ach = db.query(UserAchievement).filter(
        UserAchievement.user_id == current_user.id,
        UserAchievement.achievement_id == achievement.id
    ).first()

    if not user_ach or not user_ach.is_unlocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Achievement not unlocked"
        )

    # For now, rewards are automatically given on unlock
    # This endpoint is for future use when we implement manual claiming
    return ClaimRewardResponse(
        achievement_id=claim_request.achievement_id,
        xp_claimed=achievement.xp_reward or 0,
        coins_claimed=achievement.coin_reward or 0,
        already_claimed=True
    )


@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def seed_achievements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seed default achievements (admin/dev endpoint)"""
    count = achievement_service.seed_achievements(db)
    return {"message": f"Seeded {count} achievements"}
