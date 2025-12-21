"""
Achievement schemas
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class AchievementBase(BaseModel):
    """Base achievement schema"""
    achievement_id: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    category: str = "general"
    tier: str = "bronze"
    requirement_value: int = 1
    xp_reward: int = 0
    coin_reward: int = 0


class AchievementResponse(AchievementBase):
    """Achievement response schema"""
    id: UUID

    class Config:
        from_attributes = True


class UserAchievementResponse(BaseModel):
    """User achievement progress response"""
    id: UUID
    achievement: AchievementResponse
    current_progress: int
    is_unlocked: bool
    unlocked_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserAchievementSummary(BaseModel):
    """Summary of user's achievements"""
    total_achievements: int
    unlocked_count: int
    locked_count: int
    total_xp_earned: int
    total_coins_earned: int
    completion_percentage: float
    achievements: List[UserAchievementResponse]


class AchievementProgressUpdate(BaseModel):
    """Update achievement progress"""
    achievement_id: str
    progress_increment: int = Field(default=1, ge=1)


class AchievementProgressResponse(BaseModel):
    """Response after updating achievement progress"""
    achievement_id: str
    previous_progress: int
    current_progress: int
    requirement: int
    is_unlocked: bool
    newly_unlocked: bool
    xp_reward: Optional[int] = None
    coin_reward: Optional[int] = None


class ClaimRewardRequest(BaseModel):
    """Request to claim achievement reward"""
    achievement_id: str


class ClaimRewardResponse(BaseModel):
    """Response after claiming reward"""
    achievement_id: str
    xp_claimed: int
    coins_claimed: int
    already_claimed: bool = False


class AchievementCreate(AchievementBase):
    """Schema for creating new achievement (admin)"""
    pass
