"""
Score and game session models
"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.time_utils import utc_now


class Score(Base):
    """Individual game score entry"""
    __tablename__ = "scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Score Details
    score = Column(Integer, nullable=False, index=True)
    game_duration_seconds = Column(Integer, default=0)
    foods_eaten = Column(Integer, default=0)
    game_mode = Column(String(50), default="classic", index=True)  # 'classic', 'timed', 'endless'
    difficulty = Column(String(50), default="normal", index=True)  # 'easy', 'normal', 'hard'

    # Additional game data
    game_data = Column(JSONB, default=dict)

    # Offline-first support fields
    idempotency_key = Column(String(64), nullable=True)  # Client-generated unique key to prevent duplicates
    played_at = Column(DateTime(timezone=True), nullable=True)  # Client-provided timestamp for offline games

    # Timestamps
    created_at = Column(DateTime, default=utc_now, index=True)

    # Relationships
    user = relationship("User", back_populates="scores")

    # Composite indexes for leaderboard queries
    __table_args__ = (
        Index('ix_scores_leaderboard', 'game_mode', 'difficulty', 'score'),
        Index('ix_scores_leaderboard_user', 'user_id', 'game_mode', 'difficulty', 'score'),
        Index('ix_scores_weekly', 'game_mode', 'difficulty', 'created_at', 'score'),
        # Partial unique index for idempotency key (only when not null)
        Index('ix_scores_idempotency_key', 'idempotency_key', unique=True, postgresql_where=text('idempotency_key IS NOT NULL')),
    )


class GameReplay(Base):
    """Stored game replay data for playback"""
    __tablename__ = "game_replays"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    score_id = Column(UUID(as_uuid=True), ForeignKey("scores.id", ondelete="CASCADE"), nullable=True)

    # Replay metadata
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)

    # Replay data (stored as compressed JSON)
    replay_data = Column(JSONB, nullable=False)

    # Stats from the replay
    final_score = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    user = relationship("User")
    score = relationship("Score")
