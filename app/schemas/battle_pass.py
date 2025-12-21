"""
Battle Pass schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class BattlePassReward(BaseModel):
    """Battle Pass reward"""
    id: str
    name: str
    description: str
    type: str  # xp, coins, theme, skin, trail, powerup
    tier: str  # free, premium
    quantity: int = 1
    item_id: Optional[str] = None
    icon: str = ""


class BattlePassLevel(BaseModel):
    """Battle Pass level config"""
    level: int
    xp_required: int
    free_reward: Optional[BattlePassReward] = None
    premium_reward: Optional[BattlePassReward] = None
    is_milestone: bool = False


class BattlePassSeasonResponse(BaseModel):
    """Battle Pass season response"""
    id: UUID
    season_id: str
    name: str
    description: Optional[str] = None
    theme: str
    theme_color: str
    start_date: datetime
    end_date: datetime
    max_level: int
    price: float
    is_active: bool
    levels: List[BattlePassLevel] = []

    class Config:
        from_attributes = True


class UserBattlePassProgressResponse(BaseModel):
    """User's battle pass progress"""
    id: UUID
    user_id: UUID
    season_id: UUID
    has_premium: bool
    current_level: int
    current_xp: int
    total_xp_earned: int
    purchase_date: Optional[datetime] = None
    claimed_rewards: List[str] = []
    next_level_xp: int = 0
    progress_percent: float = 0.0

    class Config:
        from_attributes = True


class AddXPRequest(BaseModel):
    """Request to add XP"""
    xp: int = Field(..., ge=1)
    source: str = "gameplay"


class AddXPResponse(BaseModel):
    """Response after adding XP"""
    success: bool
    xp_added: int
    total_xp: int
    old_level: int
    new_level: int
    leveled_up: bool
    rewards_unlocked: List[str] = []


class ClaimRewardRequest(BaseModel):
    """Request to claim a reward"""
    level: int = Field(..., ge=1, le=100)
    tier: str  # free, premium


class ClaimRewardResponse(BaseModel):
    """Response after claiming reward"""
    success: bool
    level: int
    tier: str
    reward: Optional[BattlePassReward] = None
    message: str


class PurchasePremiumResponse(BaseModel):
    """Response after purchasing premium"""
    success: bool
    has_premium: bool
    purchase_date: Optional[datetime] = None
    message: str
