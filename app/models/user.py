"""
User model and related tables
"""
from uuid import uuid4
from sqlalchemy import Column, String, Boolean, Integer, BigInteger, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.time_utils import utc_now


class User(Base):
    """User account model"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    firebase_uid = Column(String(255), unique=True, nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    username = Column(String(20), unique=True, nullable=True, index=True)
    display_name = Column(String(255), nullable=True)
    photo_url = Column(Text, nullable=True)

    # Authentication
    auth_provider = Column(String(50), default="google")  # 'google', 'anonymous'
    is_anonymous = Column(Boolean, default=False)

    # Status
    status = Column(String(50), default="offline")  # 'online', 'offline', 'in_game'
    status_message = Column(String(255), nullable=True)
    is_public = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    # Game Statistics
    high_score = Column(Integer, default=0)
    total_games_played = Column(Integer, default=0)
    total_score = Column(BigInteger, default=0)
    level = Column(Integer, default=1)
    coins = Column(Integer, default=0)

    # Timestamps
    joined_date = Column(DateTime, default=utc_now)
    last_seen = Column(DateTime, default=utc_now, onupdate=utc_now)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    fcm_tokens = relationship("FCMToken", back_populates="user", cascade="all, delete-orphan")
    premium_content = relationship("UserPremiumContent", back_populates="user", uselist=False, cascade="all, delete-orphan")

    @property
    def is_premium(self) -> bool:
        """Check if user has premium subscription"""
        if self.premium_content is None:
            return False
        return self.premium_content.subscription_active or self.premium_content.premium_tier != "free"


class UserPreferences(Base):
    """User preferences and settings"""
    __tablename__ = "user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)

    # Game Preferences
    theme = Column(String(50), default="classic")
    sound_enabled = Column(Boolean, default=True)
    music_enabled = Column(Boolean, default=True)
    vibration_enabled = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True)

    # Additional settings stored as JSON
    settings_json = Column(JSONB, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = relationship("User", back_populates="preferences")


class FCMToken(Base):
    """FCM token for push notifications"""
    __tablename__ = "fcm_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    fcm_token = Column(Text, unique=True, nullable=False)
    platform = Column(String(50), default="flutter")
    subscribed_topics = Column(JSONB, default=list)

    # Timestamps
    registered_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = relationship("User", back_populates="fcm_tokens")


class UserPremiumContent(Base):
    """User's premium content and subscription status"""
    __tablename__ = "user_premium_content"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)

    # Subscription
    premium_tier = Column(String(50), default="free")  # 'free', 'pro'
    subscription_active = Column(Boolean, default=False)
    subscription_expires_at = Column(DateTime, nullable=True)

    # Battle Pass
    battle_pass_active = Column(Boolean, default=False)
    battle_pass_expires_at = Column(DateTime, nullable=True)
    battle_pass_tier = Column(Integer, default=0)

    # Owned Content (stored as JSON arrays)
    owned_themes = Column(JSONB, default=list)
    owned_powerups = Column(JSONB, default=list)
    owned_cosmetics = Column(JSONB, default=list)
    tournament_entries = Column(JSONB, default=dict)

    # Timestamps
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = relationship("User", back_populates="premium_content")
