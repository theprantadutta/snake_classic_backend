"""
Tournament service for managing tournaments
"""
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.models.tournament import Tournament, TournamentEntry
from app.models.user import User
from app.schemas.tournament import (
    TournamentResponse,
    TournamentListResponse,
    TournamentEntryResponse,
    TournamentLeaderboardEntry,
    TournamentLeaderboardResponse,
    TournamentCreate,
)
from app.utils.time_utils import utc_now


class TournamentService:
    """Service for tournament operations"""

    def create_tournament(
        self,
        db: Session,
        tournament_data: TournamentCreate
    ) -> Tournament:
        """Create a new tournament"""
        tournament = Tournament(
            tournament_id=tournament_data.tournament_id,
            name=tournament_data.name,
            description=tournament_data.description,
            type=tournament_data.type,
            status=tournament_data.status,
            start_date=tournament_data.start_date,
            end_date=tournament_data.end_date,
            entry_fee=tournament_data.entry_fee,
            prize_pool=tournament_data.prize_pool,
            rules=tournament_data.rules,
        )
        db.add(tournament)
        db.commit()
        db.refresh(tournament)
        return tournament

    def get_tournament(self, db: Session, tournament_id: str) -> Optional[Tournament]:
        """Get tournament by string ID"""
        return db.query(Tournament).filter(
            Tournament.tournament_id == tournament_id
        ).first()

    def get_tournament_by_uuid(self, db: Session, uuid: UUID) -> Optional[Tournament]:
        """Get tournament by UUID"""
        return db.query(Tournament).filter(Tournament.id == uuid).first()

    def list_tournaments(
        self,
        db: Session,
        status: Optional[str] = None,
        tournament_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> TournamentListResponse:
        """List tournaments with optional filters"""
        query = db.query(Tournament)

        if status:
            query = query.filter(Tournament.status == status)
        if tournament_type:
            query = query.filter(Tournament.type == tournament_type)

        total = query.count()
        tournaments = query.order_by(desc(Tournament.start_date)).offset(offset).limit(limit).all()

        # Get participant counts
        tournament_responses = []
        for t in tournaments:
            count = db.query(func.count(TournamentEntry.id)).filter(
                TournamentEntry.tournament_id == t.id
            ).scalar()
            tournament_responses.append(TournamentResponse(
                id=t.id,
                tournament_id=t.tournament_id,
                name=t.name,
                description=t.description,
                type=t.type,
                status=t.status,
                start_date=t.start_date,
                end_date=t.end_date,
                entry_fee=t.entry_fee,
                prize_pool=t.prize_pool or {},
                rules=t.rules or {},
                participant_count=count or 0,
                created_at=t.created_at
            ))

        return TournamentListResponse(
            tournaments=tournament_responses,
            total_count=total
        )

    def get_active_tournaments(self, db: Session) -> List[Tournament]:
        """Get currently active tournaments"""
        now = utc_now()
        return db.query(Tournament).filter(
            Tournament.status == "active",
            Tournament.start_date <= now,
            Tournament.end_date >= now
        ).all()

    def update_tournament_statuses(self, db: Session) -> int:
        """Update tournament statuses based on dates"""
        now = utc_now()
        updated = 0

        # Activate upcoming tournaments that have started
        upcoming = db.query(Tournament).filter(
            Tournament.status == "upcoming",
            Tournament.start_date <= now
        ).all()
        for t in upcoming:
            t.status = "active"
            updated += 1

        # Complete active tournaments that have ended
        active = db.query(Tournament).filter(
            Tournament.status == "active",
            Tournament.end_date < now
        ).all()
        for t in active:
            t.status = "completed"
            self._finalize_rankings(db, t.id)
            updated += 1

        if updated > 0:
            db.commit()
        return updated

    def join_tournament(
        self,
        db: Session,
        user_id: UUID,
        tournament_id: str
    ) -> Tuple[TournamentEntry, str]:
        """Join a tournament"""
        tournament = self.get_tournament(db, tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")

        if tournament.status == "completed":
            raise ValueError("Tournament has ended")

        # Check if already joined
        existing = db.query(TournamentEntry).filter(
            TournamentEntry.tournament_id == tournament.id,
            TournamentEntry.user_id == user_id
        ).first()

        if existing:
            return existing, "Already joined this tournament"

        # Check entry fee (TODO: deduct coins if needed)
        # if tournament.entry_fee > 0:
        #     ...

        entry = TournamentEntry(
            tournament_id=tournament.id,
            user_id=user_id,
            best_score=0,
            games_played=0,
            prize_claimed=False
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

        return entry, "Successfully joined tournament"

    def submit_score(
        self,
        db: Session,
        user_id: UUID,
        tournament_id: str,
        score: int
    ) -> Tuple[bool, int, int, int]:
        """
        Submit a score to a tournament.
        Returns: (new_best, previous_best, current_score, rank)
        """
        tournament = self.get_tournament(db, tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")

        if tournament.status != "active":
            raise ValueError("Tournament is not active")

        entry = db.query(TournamentEntry).filter(
            TournamentEntry.tournament_id == tournament.id,
            TournamentEntry.user_id == user_id
        ).first()

        if not entry:
            raise ValueError("Not joined in this tournament")

        previous_best = entry.best_score
        new_best = score > previous_best

        if new_best:
            entry.best_score = score
        entry.games_played += 1

        db.commit()

        # Calculate rank
        rank = db.query(func.count(TournamentEntry.id)).filter(
            TournamentEntry.tournament_id == tournament.id,
            TournamentEntry.best_score > entry.best_score
        ).scalar()
        rank = (rank or 0) + 1

        return new_best, previous_best, entry.best_score, rank

    def get_leaderboard(
        self,
        db: Session,
        tournament_id: str,
        user_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> TournamentLeaderboardResponse:
        """Get tournament leaderboard"""
        tournament = self.get_tournament(db, tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")

        # Get entries with user info
        query = db.query(
            TournamentEntry,
            User.username,
            User.display_name,
            User.photo_url
        ).join(
            User, TournamentEntry.user_id == User.id
        ).filter(
            TournamentEntry.tournament_id == tournament.id
        ).order_by(desc(TournamentEntry.best_score))

        total = query.count()
        results = query.offset(offset).limit(limit).all()

        entries = []
        for idx, (entry, username, display_name, photo_url) in enumerate(results):
            entries.append(TournamentLeaderboardEntry(
                rank=offset + idx + 1,
                user_id=entry.user_id,
                username=username,
                display_name=display_name,
                photo_url=photo_url,
                best_score=entry.best_score,
                games_played=entry.games_played
            ))

        # Get user's entry if provided
        user_entry = None
        if user_id:
            user_result = db.query(TournamentEntry).filter(
                TournamentEntry.tournament_id == tournament.id,
                TournamentEntry.user_id == user_id
            ).first()
            if user_result:
                user_rank = db.query(func.count(TournamentEntry.id)).filter(
                    TournamentEntry.tournament_id == tournament.id,
                    TournamentEntry.best_score > user_result.best_score
                ).scalar()
                user = db.query(User).filter(User.id == user_id).first()
                user_entry = TournamentLeaderboardEntry(
                    rank=(user_rank or 0) + 1,
                    user_id=user_id,
                    username=user.username if user else None,
                    display_name=user.display_name if user else None,
                    photo_url=user.photo_url if user else None,
                    best_score=user_result.best_score,
                    games_played=user_result.games_played
                )

        return TournamentLeaderboardResponse(
            tournament_id=tournament.id,
            tournament_name=tournament.name,
            entries=entries,
            total_participants=total,
            user_entry=user_entry
        )

    def get_user_entry(
        self,
        db: Session,
        user_id: UUID,
        tournament_id: str
    ) -> Optional[TournamentEntry]:
        """Get user's entry in a tournament"""
        tournament = self.get_tournament(db, tournament_id)
        if not tournament:
            return None

        return db.query(TournamentEntry).filter(
            TournamentEntry.tournament_id == tournament.id,
            TournamentEntry.user_id == user_id
        ).first()

    def claim_prize(
        self,
        db: Session,
        user_id: UUID,
        tournament_id: str
    ) -> Tuple[bool, str, dict]:
        """Claim prize for a tournament"""
        tournament = self.get_tournament(db, tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")

        if tournament.status != "completed":
            raise ValueError("Tournament is not completed yet")

        entry = db.query(TournamentEntry).filter(
            TournamentEntry.tournament_id == tournament.id,
            TournamentEntry.user_id == user_id
        ).first()

        if not entry:
            raise ValueError("Not participated in this tournament")

        if entry.prize_claimed:
            return False, "Prize already claimed", {}

        # Calculate prize based on rank
        prize = {}
        if entry.rank and tournament.prize_pool:
            rank_prizes = tournament.prize_pool.get("ranks", {})
            rank_str = str(entry.rank)
            if rank_str in rank_prizes:
                prize = rank_prizes[rank_str]
            elif entry.rank <= 10:
                prize = tournament.prize_pool.get("top_10", {})

        entry.prize_claimed = True
        db.commit()

        return True, "Prize claimed", prize

    def _finalize_rankings(self, db: Session, tournament_uuid: UUID):
        """Finalize rankings when tournament ends"""
        entries = db.query(TournamentEntry).filter(
            TournamentEntry.tournament_id == tournament_uuid
        ).order_by(desc(TournamentEntry.best_score)).all()

        for idx, entry in enumerate(entries):
            entry.rank = idx + 1

        db.commit()


tournament_service = TournamentService()
