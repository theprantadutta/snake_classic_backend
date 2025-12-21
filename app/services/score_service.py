"""
Score service for managing game scores
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.score import Score
from app.models.user import User
from app.schemas.score import ScoreSubmit, UserScoreStats
from app.utils.time_utils import utc_now


class ScoreService:
    """Service for score operations"""

    def submit_score(
        self,
        db: Session,
        user_id: UUID,
        score_data: ScoreSubmit
    ) -> tuple[Score, bool, Optional[int], bool]:
        """
        Submit a new score.
        Returns: (score, is_high_score, rank, was_duplicate)
        """
        # Check for existing score with same idempotency key (prevents duplicates on retry)
        if score_data.idempotency_key:
            existing = db.query(Score).filter(
                Score.idempotency_key == score_data.idempotency_key
            ).first()
            if existing:
                # Return existing score (idempotent response)
                user = db.query(User).filter(User.id == user_id).first()
                is_high_score = existing.score >= (user.high_score or 0) if user else False
                rank = self.get_score_rank(db, existing.score, existing.game_mode, existing.difficulty)
                return existing, is_high_score, rank, True  # was_duplicate=True

        # Create score record
        score = Score(
            user_id=user_id,
            score=score_data.score,
            game_duration_seconds=score_data.game_duration_seconds,
            foods_eaten=score_data.foods_eaten,
            game_mode=score_data.game_mode,
            difficulty=score_data.difficulty,
            game_data=score_data.game_data or {},
            played_at=score_data.played_at,
            idempotency_key=score_data.idempotency_key,
        )
        db.add(score)

        # Update user stats
        user = db.query(User).filter(User.id == user_id).first()
        is_high_score = False
        if user:
            user.total_games_played = (user.total_games_played or 0) + 1
            user.total_score = (user.total_score or 0) + score_data.score
            if score_data.score > (user.high_score or 0):
                user.high_score = score_data.score
                is_high_score = True

        db.commit()
        db.refresh(score)

        # Get rank
        rank = self.get_score_rank(db, score_data.score, score_data.game_mode, score_data.difficulty)

        return score, is_high_score, rank, False  # was_duplicate=False

    def get_score_rank(
        self,
        db: Session,
        score_value: int,
        game_mode: str = "classic",
        difficulty: str = "normal"
    ) -> int:
        """Get rank for a given score"""
        count = db.query(func.count(Score.id)).filter(
            Score.game_mode == game_mode,
            Score.difficulty == difficulty,
            Score.score > score_value
        ).scalar()
        return (count or 0) + 1

    def get_user_scores(
        self,
        db: Session,
        user_id: UUID,
        game_mode: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Score]:
        """Get scores for a user"""
        query = db.query(Score).filter(Score.user_id == user_id)
        if game_mode:
            query = query.filter(Score.game_mode == game_mode)
        return query.order_by(desc(Score.created_at)).offset(offset).limit(limit).all()

    def get_user_high_score(
        self,
        db: Session,
        user_id: UUID,
        game_mode: Optional[str] = None
    ) -> Optional[Score]:
        """Get user's highest score"""
        query = db.query(Score).filter(Score.user_id == user_id)
        if game_mode:
            query = query.filter(Score.game_mode == game_mode)
        return query.order_by(desc(Score.score)).first()

    def get_user_stats(self, db: Session, user_id: UUID) -> UserScoreStats:
        """Get user's score statistics"""
        scores = db.query(Score).filter(Score.user_id == user_id).all()

        if not scores:
            return UserScoreStats(
                user_id=user_id,
                high_score=0,
                total_games=0,
                total_score=0,
                average_score=0.0,
                best_game_duration=0,
                total_foods_eaten=0,
            )

        total_score = sum(s.score for s in scores)
        high_score = max(s.score for s in scores)
        best_duration = max(s.game_duration_seconds for s in scores)
        total_foods = sum(s.foods_eaten for s in scores)

        # Group by mode and difficulty
        scores_by_mode = {}
        scores_by_difficulty = {}
        for s in scores:
            mode = s.game_mode or "classic"
            diff = s.difficulty or "normal"
            if mode not in scores_by_mode or s.score > scores_by_mode[mode]:
                scores_by_mode[mode] = s.score
            if diff not in scores_by_difficulty or s.score > scores_by_difficulty[diff]:
                scores_by_difficulty[diff] = s.score

        return UserScoreStats(
            user_id=user_id,
            high_score=high_score,
            total_games=len(scores),
            total_score=total_score,
            average_score=total_score / len(scores) if scores else 0.0,
            best_game_duration=best_duration,
            total_foods_eaten=total_foods,
            scores_by_mode=scores_by_mode,
            scores_by_difficulty=scores_by_difficulty,
        )

    def get_recent_scores(
        self,
        db: Session,
        limit: int = 20,
        game_mode: Optional[str] = None
    ) -> List[Score]:
        """Get most recent scores"""
        query = db.query(Score)
        if game_mode:
            query = query.filter(Score.game_mode == game_mode)
        return query.order_by(desc(Score.created_at)).limit(limit).all()

    def submit_scores_batch(
        self,
        db: Session,
        user_id: UUID,
        scores: List[ScoreSubmit]
    ) -> tuple[List[tuple[Optional[Score], bool, Optional[int], bool, Optional[str]]], Optional[int]]:
        """
        Submit multiple scores in a single transaction (for offline sync).
        Returns: (results, new_high_score)
        Each result is (score, is_high_score, rank, was_duplicate, error)
        """
        results = []
        user = db.query(User).filter(User.id == user_id).first()
        original_high_score = user.high_score or 0 if user else 0

        for score_data in scores:
            try:
                score, is_high, rank, was_duplicate = self.submit_score(db, user_id, score_data)
                results.append((score, is_high, rank, was_duplicate, None))
            except Exception as e:
                results.append((None, False, None, False, str(e)))

        # Check if high score was updated
        if user:
            db.refresh(user)
            new_high = user.high_score if user.high_score > original_high_score else None
        else:
            new_high = None

        return results, new_high


score_service = ScoreService()
