"""
Multiplayer game models
"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.time_utils import utc_now


class MultiplayerGame(Base):
    """Multiplayer game session"""
    __tablename__ = "multiplayer_games"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    game_id = Column(String(100), unique=True, nullable=False, index=True)

    # Game configuration
    mode = Column(String(50), default="classic")  # 'classic', 'battle', 'co-op'
    status = Column(String(50), default="waiting")  # 'waiting', 'countdown', 'playing', 'finished'
    room_code = Column(String(10), nullable=True, index=True)
    max_players = Column(Integer, default=4)

    # Game state (stored as JSON)
    food_positions = Column(JSONB, default=list)
    power_ups = Column(JSONB, default=list)
    game_settings = Column(JSONB, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    # Relationships
    players = relationship("MultiplayerPlayer", back_populates="game", cascade="all, delete-orphan")


class MultiplayerPlayer(Base):
    """Player in a multiplayer game"""
    __tablename__ = "multiplayer_players"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    game_id = Column(UUID(as_uuid=True), ForeignKey("multiplayer_games.id", ondelete="CASCADE"), index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Player state
    player_index = Column(Integer, default=0)  # Player number in the game (0-3)
    score = Column(Integer, default=0)
    is_alive = Column(Boolean, default=True)
    is_ready = Column(Boolean, default=False)

    # Snake state (stored as JSON)
    snake_positions = Column(JSONB, default=list)
    direction = Column(String(10), default="right")  # 'up', 'down', 'left', 'right'
    snake_color = Column(String(50), nullable=True)

    # Timestamps
    joined_at = Column(DateTime, default=utc_now)
    last_update_at = Column(DateTime, default=utc_now)

    # Relationships
    game = relationship("MultiplayerGame", back_populates="players")
    user = relationship("User")
