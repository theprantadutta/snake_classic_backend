"""
Battle Pass API endpoints
"""
from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.battle_pass import (
    BattlePassSeasonResponse,
    BattlePassLevel,
    UserBattlePassProgressResponse,
    AddXPRequest,
    AddXPResponse,
    ClaimRewardRequest,
    ClaimRewardResponse,
    PurchasePremiumResponse,
)
from app.services.battle_pass_service import battle_pass_service

router = APIRouter(prefix="/battle-pass", tags=["battle-pass"])


@router.get("/current-season", response_model=BattlePassSeasonResponse)
async def get_current_season(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current battle pass season"""
    season = battle_pass_service.get_or_create_season(db)

    levels = []
    for level_data in (season.levels_config or []):
        levels.append(BattlePassLevel(**level_data))

    return BattlePassSeasonResponse(
        id=season.id,
        season_id=season.season_id,
        name=season.name,
        description=season.description,
        theme=season.theme,
        theme_color=season.theme_color,
        start_date=season.start_date,
        end_date=season.end_date,
        max_level=season.max_level,
        price=float(season.price),
        is_active=season.is_active,
        levels=levels
    )


@router.get("/progress", response_model=UserBattlePassProgressResponse)
async def get_my_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's battle pass progress"""
    season = battle_pass_service.get_or_create_season(db)
    progress = battle_pass_service.get_user_progress(db, current_user.id, season)
    return battle_pass_service.get_progress_response(progress, season)


@router.get("/user/{user_id}/progress", response_model=UserBattlePassProgressResponse)
async def get_user_progress(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get another user's battle pass progress"""
    season = battle_pass_service.get_or_create_season(db)
    progress = battle_pass_service.get_user_progress(db, user_id, season)
    return battle_pass_service.get_progress_response(progress, season)


@router.post("/add-xp", response_model=AddXPResponse)
async def add_xp(
    request: AddXPRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add XP to battle pass"""
    progress, old_level, new_level, leveled_up, rewards = battle_pass_service.add_xp(
        db, current_user.id, request.xp
    )

    return AddXPResponse(
        success=True,
        xp_added=request.xp,
        total_xp=progress.current_xp,
        old_level=old_level,
        new_level=new_level,
        leveled_up=leveled_up,
        rewards_unlocked=rewards
    )


@router.post("/claim-reward", response_model=ClaimRewardResponse)
async def claim_reward(
    request: ClaimRewardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Claim a battle pass reward"""
    success, reward, message = battle_pass_service.claim_reward(
        db, current_user.id, request.level, request.tier
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return ClaimRewardResponse(
        success=True,
        level=request.level,
        tier=request.tier,
        reward=reward,
        message=message
    )


@router.post("/purchase-premium", response_model=PurchasePremiumResponse)
async def purchase_premium(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activate premium battle pass (after IAP verification)"""
    success, message = battle_pass_service.purchase_premium(db, current_user.id)

    if not success:
        return PurchasePremiumResponse(
            success=False,
            has_premium=True,
            message=message
        )

    season = battle_pass_service.get_or_create_season(db)
    progress = battle_pass_service.get_user_progress(db, current_user.id, season)

    return PurchasePremiumResponse(
        success=True,
        has_premium=True,
        purchase_date=progress.purchase_date,
        message=message
    )


@router.get("/levels")
async def get_levels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all battle pass levels and rewards"""
    season = battle_pass_service.get_or_create_season(db)

    return {
        "season_id": season.season_id,
        "levels": season.levels_config or [],
        "total_levels": season.max_level
    }


@router.get("/stats")
async def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get battle pass statistics"""
    from sqlalchemy import func
    from app.models.battle_pass import UserBattlePassProgress

    season = battle_pass_service.get_or_create_season(db)

    total_users = db.query(func.count(UserBattlePassProgress.id)).filter(
        UserBattlePassProgress.season_id == season.id
    ).scalar() or 0

    premium_users = db.query(func.count(UserBattlePassProgress.id)).filter(
        UserBattlePassProgress.season_id == season.id,
        UserBattlePassProgress.has_premium == True
    ).scalar() or 0

    avg_level = db.query(func.avg(UserBattlePassProgress.current_level)).filter(
        UserBattlePassProgress.season_id == season.id
    ).scalar() or 0

    max_level_users = db.query(func.count(UserBattlePassProgress.id)).filter(
        UserBattlePassProgress.season_id == season.id,
        UserBattlePassProgress.current_level >= season.max_level
    ).scalar() or 0

    completion_rate = (max_level_users / total_users * 100) if total_users > 0 else 0

    return {
        "total_users": total_users,
        "premium_users": premium_users,
        "average_level": round(float(avg_level), 2),
        "completion_rate": round(completion_rate, 2)
    }
