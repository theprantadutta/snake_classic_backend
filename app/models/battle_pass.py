"""
Battle Pass system models
"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.time_utils import utc_now


class BattlePassSeason(Base):
    """Battle Pass season definition"""
    __tablename__ = "battle_pass_seasons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    season_id = Column(String(100), unique=True, nullable=False, index=True)

    # Season details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    theme = Column(String(50), default="default")
    theme_color = Column(String(20), default="#FFD700")

    # Schedule
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False)

    # Configuration
    max_level = Column(Integer, default=100)
    price = Column(Numeric(10, 2), default=9.99)

    # Level configuration (stored as JSON)
    # Format: [{"level": 1, "xp_required": 100, "free_reward": {...}, "premium_reward": {...}}, ...]
    levels_config = Column(JSONB, default=list)

    # Additional data
    extra_data = Column(JSONB, default=dict)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    user_progress = relationship("UserBattlePassProgress", back_populates="season", cascade="all, delete-orphan")


class UserBattlePassProgress(Base):
    """User's progress in a battle pass season"""
    __tablename__ = "user_battle_pass_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    season_id = Column(UUID(as_uuid=True), ForeignKey("battle_pass_seasons.id", ondelete="CASCADE"), index=True)

    # Premium status
    has_premium = Column(Boolean, default=False)
    purchase_date = Column(DateTime, nullable=True)

    # Progress
    current_level = Column(Integer, default=1)
    current_xp = Column(Integer, default=0)
    total_xp_earned = Column(Integer, default=0)

    # Claimed rewards (stored as JSON array of reward keys)
    claimed_rewards = Column(JSONB, default=list)

    # Timestamps
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Unique constraint - one progress per user per season
    __table_args__ = (
        UniqueConstraint('user_id', 'season_id', name='unique_user_season_progress'),
    )

    # Relationships
    user = relationship("User")
    season = relationship("BattlePassSeason", back_populates="user_progress")
