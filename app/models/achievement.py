"""
Achievement system models
"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.time_utils import utc_now


class Achievement(Base):
    """Achievement definition"""
    __tablename__ = "achievements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    achievement_id = Column(String(100), unique=True, nullable=False, index=True)

    # Achievement details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(255), nullable=True)

    # Categorization
    category = Column(String(50), default="general")  # 'general', 'score', 'social', 'streak'
    tier = Column(String(50), default="bronze")  # 'bronze', 'silver', 'gold', 'platinum'

    # Requirements
    requirement_type = Column(String(50), default="count")  # 'count', 'score', 'time'
    requirement_value = Column(Integer, default=1)

    # Rewards
    xp_reward = Column(Integer, default=0)
    coin_reward = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    is_secret = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    user_achievements = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    """User's progress on an achievement"""
    __tablename__ = "user_achievements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    achievement_id = Column(UUID(as_uuid=True), ForeignKey("achievements.id", ondelete="CASCADE"), index=True)

    # Progress
    current_progress = Column(Integer, default=0)
    is_unlocked = Column(Boolean, default=False)
    reward_claimed = Column(Boolean, default=False)

    # Timestamps
    unlocked_at = Column(DateTime, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")
