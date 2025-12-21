"""
Score and leaderboard schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class ScoreSubmit(BaseModel):
    """Schema for submitting a new score"""
    score: int = Field(..., ge=0, description="Game score")
    game_duration_seconds: int = Field(default=0, ge=0, description="Duration in seconds")
    foods_eaten: int = Field(default=0, ge=0, description="Number of foods consumed")
    game_mode: str = Field(default="classic", description="Game mode")
    difficulty: str = Field(default="normal", description="Difficulty level")
    game_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional game data")
    # Offline-first support fields
    played_at: Optional[datetime] = Field(default=None, description="Client timestamp for offline games")
    idempotency_key: Optional[str] = Field(default=None, max_length=64, description="Unique key to prevent duplicate submissions")


class ScoreResponse(BaseModel):
    """Schema for score response"""
    id: UUID
    user_id: UUID
    score: int
    game_duration_seconds: int
    foods_eaten: int
    game_mode: str
    difficulty: str
    game_data: Optional[Dict[str, Any]] = None
    played_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ScoreSubmitResponse(BaseModel):
    """Response after submitting a score"""
    score: ScoreResponse
    is_high_score: bool = False
    rank: Optional[int] = None
    achievements_unlocked: List[str] = []


class LeaderboardEntry(BaseModel):
    """Single entry in leaderboard"""
    rank: int
    user_id: UUID
    username: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    score: int
    game_mode: str
    difficulty: str
    created_at: datetime


class LeaderboardResponse(BaseModel):
    """Leaderboard response with pagination"""
    entries: List[LeaderboardEntry]
    total_count: int
    page: int
    page_size: int
    user_rank: Optional[int] = None
    user_score: Optional[int] = None


class UserScoreStats(BaseModel):
    """User's score statistics"""
    user_id: UUID
    high_score: int
    total_games: int
    total_score: int
    average_score: float
    best_game_duration: int
    total_foods_eaten: int
    scores_by_mode: Dict[str, int] = {}
    scores_by_difficulty: Dict[str, int] = {}


class DailyStats(BaseModel):
    """Daily score statistics"""
    date: str
    games_played: int
    high_score: int
    total_score: int


# Batch submission schemas for offline sync
class BatchScoreSubmit(BaseModel):
    """Schema for submitting multiple scores at once (for offline sync)"""
    scores: List[ScoreSubmit] = Field(..., min_length=1, max_length=50)


class BatchScoreResult(BaseModel):
    """Result for a single score in batch submission"""
    index: int
    success: bool
    score: Optional[ScoreResponse] = None
    is_high_score: bool = False
    rank: Optional[int] = None
    error: Optional[str] = None
    was_duplicate: bool = False


class BatchScoreSubmitResponse(BaseModel):
    """Response for batch score submission"""
    total: int
    successful: int
    failed: int
    duplicates: int
    results: List[BatchScoreResult]
    new_high_score: Optional[int] = None  # User's new high score if updated
    achievements_unlocked: List[str] = []
