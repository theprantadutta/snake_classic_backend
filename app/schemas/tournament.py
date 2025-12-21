"""
Tournament schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class TournamentBase(BaseModel):
    """Base tournament schema"""
    tournament_id: str
    name: str
    description: Optional[str] = None
    type: str = "daily"
    status: str = "upcoming"
    start_date: datetime
    end_date: datetime
    entry_fee: int = 0
    prize_pool: Dict[str, Any] = {}
    rules: Dict[str, Any] = {}


class TournamentResponse(TournamentBase):
    """Tournament response schema"""
    id: UUID
    participant_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class TournamentListResponse(BaseModel):
    """List of tournaments"""
    tournaments: List[TournamentResponse]
    total_count: int


class TournamentEntryResponse(BaseModel):
    """Tournament entry response"""
    id: UUID
    tournament_id: UUID
    user_id: UUID
    best_score: int
    games_played: int
    rank: Optional[int] = None
    prize_claimed: bool
    joined_at: datetime

    class Config:
        from_attributes = True


class TournamentLeaderboardEntry(BaseModel):
    """Single entry in tournament leaderboard"""
    rank: int
    user_id: UUID
    username: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    best_score: int
    games_played: int


class TournamentLeaderboardResponse(BaseModel):
    """Tournament leaderboard response"""
    tournament_id: UUID
    tournament_name: str
    entries: List[TournamentLeaderboardEntry]
    total_participants: int
    user_entry: Optional[TournamentLeaderboardEntry] = None


class TournamentJoinResponse(BaseModel):
    """Response after joining a tournament"""
    success: bool
    message: str
    entry: Optional[TournamentEntryResponse] = None


class TournamentScoreSubmit(BaseModel):
    """Submit a score to a tournament"""
    score: int = Field(..., ge=0)
    game_duration_seconds: int = Field(default=0, ge=0)
    foods_eaten: int = Field(default=0, ge=0)


class TournamentScoreResponse(BaseModel):
    """Response after submitting tournament score"""
    success: bool
    new_best: bool
    previous_best: int
    current_score: int
    rank: int


class TournamentCreate(TournamentBase):
    """Schema for creating tournaments (admin)"""
    pass


class ClaimPrizeResponse(BaseModel):
    """Response after claiming prize"""
    success: bool
    message: str
    prize: Dict[str, Any] = {}
    already_claimed: bool = False
