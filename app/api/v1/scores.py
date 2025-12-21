"""
Score API endpoints
"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.score import (
    ScoreSubmit,
    ScoreResponse,
    ScoreSubmitResponse,
    UserScoreStats,
    BatchScoreSubmit,
    BatchScoreResult,
    BatchScoreSubmitResponse,
)
from app.services.score_service import score_service
from app.services.achievement_service import achievement_service

router = APIRouter(prefix="/scores", tags=["scores"])


@router.post("", response_model=ScoreSubmitResponse, status_code=status.HTTP_201_CREATED)
async def submit_score(
    score_data: ScoreSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a new game score"""
    score, is_high_score, rank, was_duplicate = score_service.submit_score(
        db, current_user.id, score_data
    )

    # Only check achievements for new scores (not duplicates)
    achievements_unlocked = []
    if not was_duplicate:
        unlocked = achievement_service.check_score_achievements(
            db=db,
            user_id=current_user.id,
            score=score_data.score,
            foods_eaten=score_data.foods_eaten,
            duration=score_data.game_duration_seconds
        )
        achievements_unlocked = [a.achievement_id for a in unlocked if a.newly_unlocked]

    return ScoreSubmitResponse(
        score=ScoreResponse.model_validate(score),
        is_high_score=is_high_score,
        rank=rank,
        achievements_unlocked=achievements_unlocked
    )


@router.get("/me", response_model=List[ScoreResponse])
async def get_my_scores(
    game_mode: Optional[str] = Query(None, description="Filter by game mode"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's scores"""
    scores = score_service.get_user_scores(
        db, current_user.id, game_mode, limit, offset
    )
    return [ScoreResponse.model_validate(s) for s in scores]


@router.get("/me/stats", response_model=UserScoreStats)
async def get_my_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's score statistics"""
    return score_service.get_user_stats(db, current_user.id)


@router.get("/user/{user_id}", response_model=List[ScoreResponse])
async def get_user_scores(
    user_id: UUID,
    game_mode: Optional[str] = Query(None, description="Filter by game mode"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get scores for a specific user"""
    scores = score_service.get_user_scores(db, user_id, game_mode, limit, offset)
    return [ScoreResponse.model_validate(s) for s in scores]


@router.get("/user/{user_id}/stats", response_model=UserScoreStats)
async def get_user_stats(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get score statistics for a specific user"""
    return score_service.get_user_stats(db, user_id)


@router.get("/recent", response_model=List[ScoreResponse])
async def get_recent_scores(
    game_mode: Optional[str] = Query(None, description="Filter by game mode"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recent scores from all users"""
    scores = score_service.get_recent_scores(db, limit, game_mode)
    return [ScoreResponse.model_validate(s) for s in scores]


@router.post("/batch", response_model=BatchScoreSubmitResponse, status_code=status.HTTP_201_CREATED)
async def submit_scores_batch(
    batch_data: BatchScoreSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit multiple game scores in a single request (for offline sync)"""
    raw_results, new_high = score_service.submit_scores_batch(
        db, current_user.id, batch_data.scores
    )

    results = []
    successful = 0
    failed = 0
    duplicates = 0
    all_achievements_unlocked = []

    for i, (score, is_high, rank, was_dup, error) in enumerate(raw_results):
        if error:
            failed += 1
            results.append(BatchScoreResult(
                index=i, success=False, error=error, was_duplicate=False
            ))
        elif was_dup:
            duplicates += 1
            successful += 1  # Duplicates are still "successful" (idempotent)
            results.append(BatchScoreResult(
                index=i, success=True,
                score=ScoreResponse.model_validate(score),
                is_high_score=is_high, rank=rank, was_duplicate=True
            ))
        else:
            successful += 1
            # Check achievements for new scores
            score_data = batch_data.scores[i]
            unlocked = achievement_service.check_score_achievements(
                db=db,
                user_id=current_user.id,
                score=score_data.score,
                foods_eaten=score_data.foods_eaten,
                duration=score_data.game_duration_seconds
            )
            newly_unlocked = [a.achievement_id for a in unlocked if a.newly_unlocked]
            all_achievements_unlocked.extend(newly_unlocked)

            results.append(BatchScoreResult(
                index=i, success=True,
                score=ScoreResponse.model_validate(score),
                is_high_score=is_high, rank=rank, was_duplicate=False
            ))

    return BatchScoreSubmitResponse(
        total=len(batch_data.scores),
        successful=successful,
        failed=failed,
        duplicates=duplicates,
        results=results,
        new_high_score=new_high,
        achievements_unlocked=list(set(all_achievements_unlocked))  # Deduplicate
    )
