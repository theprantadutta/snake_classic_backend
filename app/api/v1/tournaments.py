"""
Tournament API endpoints
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.tournament import (
    TournamentResponse,
    TournamentListResponse,
    TournamentEntryResponse,
    TournamentLeaderboardResponse,
    TournamentJoinResponse,
    TournamentScoreSubmit,
    TournamentScoreResponse,
    ClaimPrizeResponse,
)
from app.services.tournament_service import tournament_service

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.get("", response_model=TournamentListResponse)
async def list_tournaments(
    status: Optional[str] = Query(None, description="Filter by status"),
    type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all tournaments"""
    return tournament_service.list_tournaments(db, status, type, limit, offset)


@router.get("/active", response_model=TournamentListResponse)
async def get_active_tournaments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get currently active tournaments"""
    # First update statuses
    tournament_service.update_tournament_statuses(db)
    return tournament_service.list_tournaments(db, status="active")


@router.get("/{tournament_id}", response_model=TournamentResponse)
async def get_tournament(
    tournament_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tournament details"""
    from sqlalchemy import func
    from app.models.tournament import Tournament, TournamentEntry

    tournament = tournament_service.get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found"
        )

    count = db.query(func.count(TournamentEntry.id)).filter(
        TournamentEntry.tournament_id == tournament.id
    ).scalar()

    return TournamentResponse(
        id=tournament.id,
        tournament_id=tournament.tournament_id,
        name=tournament.name,
        description=tournament.description,
        type=tournament.type,
        status=tournament.status,
        start_date=tournament.start_date,
        end_date=tournament.end_date,
        entry_fee=tournament.entry_fee,
        prize_pool=tournament.prize_pool or {},
        rules=tournament.rules or {},
        participant_count=count or 0,
        created_at=tournament.created_at
    )


@router.post("/{tournament_id}/join", response_model=TournamentJoinResponse)
async def join_tournament(
    tournament_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Join a tournament"""
    try:
        entry, message = tournament_service.join_tournament(
            db, current_user.id, tournament_id
        )
        return TournamentJoinResponse(
            success=True,
            message=message,
            entry=TournamentEntryResponse.model_validate(entry)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{tournament_id}/score", response_model=TournamentScoreResponse)
async def submit_tournament_score(
    tournament_id: str,
    score_data: TournamentScoreSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a score to a tournament"""
    try:
        new_best, previous_best, current_score, rank = tournament_service.submit_score(
            db, current_user.id, tournament_id, score_data.score
        )
        return TournamentScoreResponse(
            success=True,
            new_best=new_best,
            previous_best=previous_best,
            current_score=current_score,
            rank=rank
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{tournament_id}/leaderboard", response_model=TournamentLeaderboardResponse)
async def get_tournament_leaderboard(
    tournament_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tournament leaderboard"""
    try:
        return tournament_service.get_leaderboard(
            db, tournament_id, current_user.id, limit, offset
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{tournament_id}/my-entry", response_model=TournamentEntryResponse)
async def get_my_tournament_entry(
    tournament_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get my entry in a tournament"""
    entry = tournament_service.get_user_entry(db, current_user.id, tournament_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not joined in this tournament"
        )
    return TournamentEntryResponse.model_validate(entry)


@router.post("/{tournament_id}/claim-prize", response_model=ClaimPrizeResponse)
async def claim_tournament_prize(
    tournament_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Claim prize for a completed tournament"""
    try:
        success, message, prize = tournament_service.claim_prize(
            db, current_user.id, tournament_id
        )
        return ClaimPrizeResponse(
            success=success,
            message=message,
            prize=prize,
            already_claimed=not success
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
