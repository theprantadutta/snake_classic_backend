"""
Tournament system models
"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.time_utils import utc_now


class Tournament(Base):
    """Tournament definition"""
    __tablename__ = "tournaments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tournament_id = Column(String(100), unique=True, nullable=False, index=True)

    # Tournament details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Type and status
    type = Column(String(50), default="daily")  # 'daily', 'weekly', 'special'
    status = Column(String(50), default="upcoming")  # 'upcoming', 'active', 'completed'

    # Schedule
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False)

    # Entry requirements
    entry_fee = Column(Integer, default=0)  # In coins
    min_level = Column(Integer, default=1)
    max_players = Column(Integer, nullable=True)

    # Prizes (stored as JSON)
    prize_pool = Column(JSONB, default=dict)

    # Rules (stored as JSON)
    rules = Column(JSONB, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    entries = relationship("TournamentEntry", back_populates="tournament", cascade="all, delete-orphan")


class TournamentEntry(Base):
    """User's entry in a tournament"""
    __tablename__ = "tournament_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tournament_id = Column(UUID(as_uuid=True), ForeignKey("tournaments.id", ondelete="CASCADE"), index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Performance
    best_score = Column(Integer, default=0)
    games_played = Column(Integer, default=0)
    rank = Column(Integer, nullable=True)

    # Prize status
    prize_claimed = Column(Boolean, default=False)
    prize_amount = Column(JSONB, nullable=True)  # What prize was won

    # Timestamps
    joined_at = Column(DateTime, default=utc_now)
    last_played_at = Column(DateTime, nullable=True)

    # Unique constraint - one entry per user per tournament
    __table_args__ = (
        UniqueConstraint('tournament_id', 'user_id', name='unique_tournament_entry'),
    )

    # Relationships
    tournament = relationship("Tournament", back_populates="entries")
    user = relationship("User")
