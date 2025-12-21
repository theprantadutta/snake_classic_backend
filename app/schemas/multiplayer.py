"""
Multiplayer game schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class Position(BaseModel):
    """2D position"""
    x: int
    y: int


class PlayerState(BaseModel):
    """Player state in a multiplayer game"""
    user_id: UUID
    username: Optional[str] = None
    display_name: Optional[str] = None
    player_index: int
    score: int = 0
    is_alive: bool = True
    snake_positions: List[Position] = []
    direction: str = "right"
    color: str = "#4CAF50"


class GameCreateRequest(BaseModel):
    """Request to create a new multiplayer game"""
    mode: str = Field(default="classic", description="Game mode")
    max_players: int = Field(default=4, ge=2, le=8)
    grid_size: int = Field(default=20, ge=10, le=40)
    speed: int = Field(default=100, ge=50, le=200)


class GameJoinRequest(BaseModel):
    """Request to join a game"""
    room_code: str = Field(..., min_length=4, max_length=10)


class GameResponse(BaseModel):
    """Multiplayer game response"""
    id: UUID
    game_id: str
    mode: str
    status: str
    room_code: str
    max_players: int
    current_players: int
    players: List[PlayerState]
    food_positions: List[Position] = []
    power_ups: List[Dict[str, Any]] = []
    grid_size: int = 20
    created_at: datetime
    started_at: Optional[datetime] = None


class GameStateUpdate(BaseModel):
    """Game state update from server"""
    game_id: str
    status: str
    players: List[PlayerState]
    food_positions: List[Position]
    power_ups: List[Dict[str, Any]] = []
    countdown: Optional[int] = None
    winner_id: Optional[UUID] = None


class PlayerAction(BaseModel):
    """Player action sent via WebSocket"""
    action: str  # 'move', 'ready', 'leave'
    direction: Optional[str] = None  # 'up', 'down', 'left', 'right'
    data: Optional[Dict[str, Any]] = None


class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str  # 'game_state', 'player_joined', 'player_left', 'countdown', 'game_over', 'error'
    data: Dict[str, Any]


class GameCreateResponse(BaseModel):
    """Response after creating a game"""
    success: bool
    message: str
    game: Optional[GameResponse] = None
    room_code: Optional[str] = None


class GameJoinResponse(BaseModel):
    """Response after joining a game"""
    success: bool
    message: str
    game: Optional[GameResponse] = None
    player_index: Optional[int] = None
