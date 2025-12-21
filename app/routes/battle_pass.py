"""
Battle Pass endpoints for Snake Classic game.
Handles Battle Pass progression, XP, and reward distribution.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
import json

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/battle-pass",
    tags=["battle-pass"],
    responses={
        500: {"description": "Internal server error"},
        400: {"description": "Bad request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
    },
)

# Pydantic models for request/response validation

class BattlePassSeasonInfo(BaseModel):
    """Battle Pass season information."""
    id: str
    name: str
    description: str
    theme: str
    start_date: datetime
    end_date: datetime
    max_level: int = 100
    price: float
    theme_color: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BattlePassReward(BaseModel):
    """Battle Pass reward information."""
    id: str
    name: str
    description: str
    type: str  # xp, coins, theme, skin, trail, powerUp, tournamentEntry, title, avatar, special
    tier: str  # free, premium
    quantity: int = 1
    item_id: Optional[str] = None
    icon: str = "🎁"
    color: str = "#2196F3"
    is_special: bool = False

class BattlePassLevel(BaseModel):
    """Battle Pass level information."""
    level: int
    xp_required: int
    free_reward: Optional[BattlePassReward] = None
    premium_reward: Optional[BattlePassReward] = None
    is_milestone: bool = False

class UserBattlePassProgress(BaseModel):
    """User's Battle Pass progress."""
    user_id: str
    season_id: str
    has_premium: bool
    current_level: int
    current_xp: int
    purchase_date: Optional[datetime] = None
    claimed_rewards: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)

class AddXPRequest(BaseModel):
    """Request to add XP to user's Battle Pass."""
    user_id: str
    xp: int
    source: str = "gameplay"  # gameplay, achievement, bonus, etc.
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ClaimRewardRequest(BaseModel):
    """Request to claim a Battle Pass reward."""
    user_id: str
    level: int
    tier: str  # free or premium
    reward_id: str

class BattlePassStatsResponse(BaseModel):
    """Battle Pass statistics response."""
    total_users: int
    premium_users: int
    average_level: float
    top_levels: List[Dict[str, Any]]
    completion_rate: float

# In-memory storage for demo purposes
# In production, this should be a proper database
current_season: Dict[str, Any] = {
    "id": "season_cosmic_2025",
    "name": "Cosmic Serpent Season",
    "description": "Explore the cosmos with exclusive space-themed rewards",
    "theme": "cosmic",
    "start_date": datetime.now() - timedelta(days=5),
    "end_date": datetime.now() + timedelta(days=55),
    "max_level": 100,
    "price": 9.99,
    "theme_color": "#4B0082",
    "metadata": {
        "featured_skins": ["galaxy", "cosmic", "crystal"],
        "featured_themes": ["space", "cyberpunk"],
        "special_events": ["cosmic_tournament", "starlight_challenge"],
    }
}

user_battle_pass_progress: Dict[str, Dict] = {}
season_levels: Dict[int, BattlePassLevel] = {}

# Initialize sample Battle Pass levels
def _initialize_battle_pass_levels():
    """Initialize Battle Pass levels with rewards."""
    global season_levels
    
    for level in range(1, 101):
        xp_required = 100 + (level * 5)  # Progressive XP requirement
        is_milestone = level % 10 == 0
        
        free_reward = None
        premium_reward = None
        
        # Free rewards every 5 levels
        if level % 5 == 0:
            free_reward = BattlePassReward(
                id=f"free_{level}",
                name=f"Free Reward Level {level}",
                description=f"Free reward for reaching level {level}",
                type="xp" if level % 10 != 0 else "coins",
                tier="free",
                quantity=25 if level % 10 != 0 else 50,
                icon="⭐" if level % 10 != 0 else "🪙"
            )
        
        # Premium rewards every 3 levels
        if level % 3 == 0:
            reward_type = "skin" if level % 25 == 0 else "coins"
            premium_reward = BattlePassReward(
                id=f"premium_{level}",
                name=f"Premium Reward Level {level}",
                description=f"Premium reward for reaching level {level}",
                type=reward_type,
                tier="premium",
                quantity=1 if reward_type == "skin" else 100,
                is_special=is_milestone,
                icon="🐍" if reward_type == "skin" else "💰",
                color="#FFD700" if is_milestone else "#FF6B35"
            )
        
        season_levels[level] = BattlePassLevel(
            level=level,
            xp_required=xp_required,
            free_reward=free_reward,
            premium_reward=premium_reward,
            is_milestone=is_milestone
        )

# Initialize levels on startup
_initialize_battle_pass_levels()

@router.get("/current-season", response_model=BattlePassSeasonInfo)
async def get_current_season() -> BattlePassSeasonInfo:
    """Get current Battle Pass season information."""
    try:
        logger.info("Getting current Battle Pass season")
        return BattlePassSeasonInfo(**current_season)
    except Exception as e:
        logger.error(f"Error getting current season: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get current season"
        )

@router.get("/user/{user_id}/progress", response_model=UserBattlePassProgress)
async def get_user_progress(user_id: str) -> UserBattlePassProgress:
    """Get user's Battle Pass progress."""
    try:
        logger.info(f"Getting Battle Pass progress for user {user_id}")
        
        if user_id not in user_battle_pass_progress:
            # Create new progress for user
            user_battle_pass_progress[user_id] = {
                "user_id": user_id,
                "season_id": current_season["id"],
                "has_premium": False,
                "current_level": 1,
                "current_xp": 0,
                "purchase_date": None,
                "claimed_rewards": [],
                "last_updated": datetime.now(),
            }
        
        return UserBattlePassProgress(**user_battle_pass_progress[user_id])
    except Exception as e:
        logger.error(f"Error getting user progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user progress"
        )

@router.post("/user/{user_id}/add-xp")
async def add_user_xp(
    user_id: str, 
    request: AddXPRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Add XP to user's Battle Pass."""
    try:
        logger.info(f"Adding {request.xp} XP to user {user_id}")
        
        # Get or create user progress
        if user_id not in user_battle_pass_progress:
            user_battle_pass_progress[user_id] = {
                "user_id": user_id,
                "season_id": current_season["id"],
                "has_premium": False,
                "current_level": 1,
                "current_xp": 0,
                "purchase_date": None,
                "claimed_rewards": [],
                "last_updated": datetime.now(),
            }
        
        user_progress = user_battle_pass_progress[user_id]
        old_level = user_progress["current_level"]
        
        # Add XP
        user_progress["current_xp"] += request.xp
        user_progress["last_updated"] = datetime.now()
        
        # Calculate new level
        total_xp = user_progress["current_xp"]
        new_level = 1
        xp_accumulated = 0
        
        for level in range(1, 101):
            level_xp = season_levels[level].xp_required
            if total_xp >= xp_accumulated + level_xp:
                xp_accumulated += level_xp
                new_level = level + 1
            else:
                break
        
        new_level = min(new_level, 100)  # Cap at max level
        user_progress["current_level"] = new_level
        
        level_up = new_level > old_level
        
        # Schedule background tasks for level up rewards
        if level_up:
            background_tasks.add_task(
                _handle_level_up_rewards,
                user_id,
                old_level,
                new_level
            )
        
        return {
            "success": True,
            "user_id": user_id,
            "xp_added": request.xp,
            "total_xp": user_progress["current_xp"],
            "old_level": old_level,
            "new_level": new_level,
            "level_up": level_up,
            "source": request.source,
            "message": f"Added {request.xp} XP" + (f" and leveled up to {new_level}!" if level_up else "")
        }
        
    except Exception as e:
        logger.error(f"Error adding XP to user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add XP: {str(e)}"
        )

@router.post("/user/{user_id}/claim-reward")
async def claim_reward(
    user_id: str,
    request: ClaimRewardRequest
) -> Dict[str, Any]:
    """Claim a Battle Pass reward."""
    try:
        logger.info(f"User {user_id} claiming reward at level {request.level} ({request.tier})")
        
        # Get user progress
        if user_id not in user_battle_pass_progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User Battle Pass progress not found"
            )
        
        user_progress = user_battle_pass_progress[user_id]
        
        # Check if user has reached the required level
        if user_progress["current_level"] < request.level:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User has not reached level {request.level} yet"
            )
        
        # Check if reward is premium and user has premium
        if request.tier == "premium" and not user_progress["has_premium"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Premium Battle Pass required to claim premium rewards"
            )
        
        # Check if reward already claimed
        reward_key = f"{request.level}_{request.tier}"
        if reward_key in user_progress["claimed_rewards"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reward already claimed"
            )
        
        # Get the reward info
        level_data = season_levels.get(request.level)
        if not level_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Level {request.level} not found"
            )
        
        reward = level_data.free_reward if request.tier == "free" else level_data.premium_reward
        if not reward:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No {request.tier} reward available at level {request.level}"
            )
        
        # Mark reward as claimed
        user_progress["claimed_rewards"].append(reward_key)
        user_progress["last_updated"] = datetime.now()
        
        return {
            "success": True,
            "user_id": user_id,
            "level": request.level,
            "tier": request.tier,
            "reward": {
                "id": reward.id,
                "name": reward.name,
                "type": reward.type,
                "quantity": reward.quantity,
                "item_id": reward.item_id,
            },
            "message": f"Successfully claimed {reward.name}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error claiming reward for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to claim reward: {str(e)}"
        )

@router.post("/user/{user_id}/purchase-premium")
async def purchase_premium(user_id: str) -> Dict[str, Any]:
    """Mark user as having premium Battle Pass."""
    try:
        logger.info(f"Activating premium Battle Pass for user {user_id}")
        
        # Get or create user progress
        if user_id not in user_battle_pass_progress:
            user_battle_pass_progress[user_id] = {
                "user_id": user_id,
                "season_id": current_season["id"],
                "has_premium": False,
                "current_level": 1,
                "current_xp": 0,
                "purchase_date": None,
                "claimed_rewards": [],
                "last_updated": datetime.now(),
            }
        
        user_progress = user_battle_pass_progress[user_id]
        user_progress["has_premium"] = True
        user_progress["purchase_date"] = datetime.now()
        user_progress["last_updated"] = datetime.now()
        
        return {
            "success": True,
            "user_id": user_id,
            "has_premium": True,
            "purchase_date": user_progress["purchase_date"],
            "message": "Premium Battle Pass activated successfully!"
        }
        
    except Exception as e:
        logger.error(f"Error activating premium Battle Pass for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate premium Battle Pass: {str(e)}"
        )

@router.get("/levels")
async def get_all_levels() -> Dict[str, Any]:
    """Get all Battle Pass levels and rewards."""
    try:
        logger.info("Getting all Battle Pass levels")
        
        levels_data = []
        for level in range(1, 101):
            level_data = season_levels[level]
            levels_data.append({
                "level": level_data.level,
                "xp_required": level_data.xp_required,
                "free_reward": level_data.free_reward.dict() if level_data.free_reward else None,
                "premium_reward": level_data.premium_reward.dict() if level_data.premium_reward else None,
                "is_milestone": level_data.is_milestone,
            })
        
        return {
            "season_id": current_season["id"],
            "levels": levels_data,
            "total_levels": len(levels_data)
        }
        
    except Exception as e:
        logger.error(f"Error getting Battle Pass levels: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get Battle Pass levels"
        )

@router.get("/stats", response_model=BattlePassStatsResponse)
async def get_battle_pass_stats() -> BattlePassStatsResponse:
    """Get Battle Pass statistics."""
    try:
        logger.info("Getting Battle Pass statistics")
        
        total_users = len(user_battle_pass_progress)
        premium_users = sum(1 for user in user_battle_pass_progress.values() if user["has_premium"])
        
        if total_users == 0:
            return BattlePassStatsResponse(
                total_users=0,
                premium_users=0,
                average_level=0.0,
                top_levels=[],
                completion_rate=0.0
            )
        
        # Calculate average level
        total_levels = sum(user["current_level"] for user in user_battle_pass_progress.values())
        average_level = total_levels / total_users
        
        # Get top levels
        top_users = sorted(
            user_battle_pass_progress.values(),
            key=lambda x: (x["current_level"], x["current_xp"]),
            reverse=True
        )[:10]
        
        top_levels = [
            {
                "user_id": user["user_id"],
                "level": user["current_level"],
                "xp": user["current_xp"],
                "has_premium": user["has_premium"]
            }
            for user in top_users
        ]
        
        # Calculate completion rate (users who reached max level)
        max_level_users = sum(1 for user in user_battle_pass_progress.values() if user["current_level"] >= 100)
        completion_rate = (max_level_users / total_users) * 100
        
        return BattlePassStatsResponse(
            total_users=total_users,
            premium_users=premium_users,
            average_level=round(average_level, 2),
            top_levels=top_levels,
            completion_rate=round(completion_rate, 2)
        )
        
    except Exception as e:
        logger.error(f"Error getting Battle Pass stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get Battle Pass statistics"
        )

# Helper functions

async def _handle_level_up_rewards(user_id: str, old_level: int, new_level: int):
    """Handle automatic reward distribution for level ups."""
    logger.info(f"Handling level up rewards for user {user_id}: {old_level} -> {new_level}")
    
    # This could trigger notifications, grant automatic rewards, etc.
    # For now, just log the level up
    levels_gained = new_level - old_level
    logger.info(f"User {user_id} gained {levels_gained} levels!")