"""
Leaderboard service for ranking and leaderboard queries
"""
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.models.score import Score
from app.models.user import User
from app.models.social import Friendship
from app.schemas.score import LeaderboardEntry, LeaderboardResponse
from app.utils.time_utils import utc_now


class LeaderboardService:
    """Service for leaderboard operations"""

    def get_global_leaderboard(
        self,
        db: Session,
        game_mode: str = "classic",
        difficulty: str = "normal",
        page: int = 1,
        page_size: int = 50,
        current_user_id: Optional[UUID] = None
    ) -> LeaderboardResponse:
        """Get global leaderboard - top scores all time"""
        # Subquery for max score per user
        subquery = db.query(
            Score.user_id,
            func.max(Score.score).label('max_score'),
            func.max(Score.created_at).label('latest_date')
        ).filter(
            Score.game_mode == game_mode,
            Score.difficulty == difficulty
        ).group_by(Score.user_id).subquery()

        # Main query joining with users
        query = db.query(
            User.id,
            User.username,
            User.display_name,
            User.photo_url,
            subquery.c.max_score,
            subquery.c.latest_date
        ).join(
            subquery, User.id == subquery.c.user_id
        ).order_by(desc(subquery.c.max_score))

        # Get total count
        total_count = query.count()

        # Paginate
        offset = (page - 1) * page_size
        results = query.offset(offset).limit(page_size).all()

        # Build entries with rank
        entries = []
        for idx, row in enumerate(results):
            entries.append(LeaderboardEntry(
                rank=offset + idx + 1,
                user_id=row[0],
                username=row[1],
                display_name=row[2],
                photo_url=row[3],
                score=row[4],
                game_mode=game_mode,
                difficulty=difficulty,
                created_at=row[5]
            ))

        # Get current user's rank and score
        user_rank = None
        user_score = None
        if current_user_id:
            user_rank, user_score = self._get_user_rank(
                db, current_user_id, game_mode, difficulty
            )

        return LeaderboardResponse(
            entries=entries,
            total_count=total_count,
            page=page,
            page_size=page_size,
            user_rank=user_rank,
            user_score=user_score
        )

    def get_weekly_leaderboard(
        self,
        db: Session,
        game_mode: str = "classic",
        difficulty: str = "normal",
        page: int = 1,
        page_size: int = 50,
        current_user_id: Optional[UUID] = None
    ) -> LeaderboardResponse:
        """Get weekly leaderboard - top scores this week"""
        week_ago = utc_now() - timedelta(days=7)
        return self._get_time_filtered_leaderboard(
            db, game_mode, difficulty, week_ago, page, page_size, current_user_id
        )

    def get_daily_leaderboard(
        self,
        db: Session,
        game_mode: str = "classic",
        difficulty: str = "normal",
        page: int = 1,
        page_size: int = 50,
        current_user_id: Optional[UUID] = None
    ) -> LeaderboardResponse:
        """Get daily leaderboard - top scores today"""
        today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self._get_time_filtered_leaderboard(
            db, game_mode, difficulty, today_start, page, page_size, current_user_id
        )

    def get_friends_leaderboard(
        self,
        db: Session,
        user_id: UUID,
        game_mode: str = "classic",
        difficulty: str = "normal",
        page: int = 1,
        page_size: int = 50
    ) -> LeaderboardResponse:
        """Get leaderboard for user's friends"""
        # Get friend IDs
        friend_ids = db.query(Friendship.friend_id).filter(
            Friendship.user_id == user_id,
            Friendship.status == "accepted"
        ).all()
        friend_ids = [f[0] for f in friend_ids]
        friend_ids.append(user_id)  # Include self

        # Subquery for max score per user among friends
        subquery = db.query(
            Score.user_id,
            func.max(Score.score).label('max_score'),
            func.max(Score.created_at).label('latest_date')
        ).filter(
            Score.user_id.in_(friend_ids),
            Score.game_mode == game_mode,
            Score.difficulty == difficulty
        ).group_by(Score.user_id).subquery()

        # Main query
        query = db.query(
            User.id,
            User.username,
            User.display_name,
            User.photo_url,
            subquery.c.max_score,
            subquery.c.latest_date
        ).join(
            subquery, User.id == subquery.c.user_id
        ).order_by(desc(subquery.c.max_score))

        total_count = query.count()
        offset = (page - 1) * page_size
        results = query.offset(offset).limit(page_size).all()

        entries = []
        for idx, row in enumerate(results):
            entries.append(LeaderboardEntry(
                rank=offset + idx + 1,
                user_id=row[0],
                username=row[1],
                display_name=row[2],
                photo_url=row[3],
                score=row[4],
                game_mode=game_mode,
                difficulty=difficulty,
                created_at=row[5]
            ))

        # Get user's rank within friends
        user_rank = None
        user_score = None
        user_high = db.query(func.max(Score.score)).filter(
            Score.user_id == user_id,
            Score.game_mode == game_mode,
            Score.difficulty == difficulty
        ).scalar()

        if user_high:
            user_score = user_high
            # Count friends with higher scores
            higher_count = db.query(func.count()).select_from(subquery).filter(
                subquery.c.max_score > user_high
            ).scalar()
            user_rank = (higher_count or 0) + 1

        return LeaderboardResponse(
            entries=entries,
            total_count=total_count,
            page=page,
            page_size=page_size,
            user_rank=user_rank,
            user_score=user_score
        )

    def _get_time_filtered_leaderboard(
        self,
        db: Session,
        game_mode: str,
        difficulty: str,
        since: datetime,
        page: int,
        page_size: int,
        current_user_id: Optional[UUID]
    ) -> LeaderboardResponse:
        """Get leaderboard filtered by time"""
        # Subquery for max score per user within timeframe
        subquery = db.query(
            Score.user_id,
            func.max(Score.score).label('max_score'),
            func.max(Score.created_at).label('latest_date')
        ).filter(
            Score.game_mode == game_mode,
            Score.difficulty == difficulty,
            Score.created_at >= since
        ).group_by(Score.user_id).subquery()

        # Main query
        query = db.query(
            User.id,
            User.username,
            User.display_name,
            User.photo_url,
            subquery.c.max_score,
            subquery.c.latest_date
        ).join(
            subquery, User.id == subquery.c.user_id
        ).order_by(desc(subquery.c.max_score))

        total_count = query.count()
        offset = (page - 1) * page_size
        results = query.offset(offset).limit(page_size).all()

        entries = []
        for idx, row in enumerate(results):
            entries.append(LeaderboardEntry(
                rank=offset + idx + 1,
                user_id=row[0],
                username=row[1],
                display_name=row[2],
                photo_url=row[3],
                score=row[4],
                game_mode=game_mode,
                difficulty=difficulty,
                created_at=row[5]
            ))

        # Get current user's rank
        user_rank = None
        user_score = None
        if current_user_id:
            user_high = db.query(func.max(Score.score)).filter(
                Score.user_id == current_user_id,
                Score.game_mode == game_mode,
                Score.difficulty == difficulty,
                Score.created_at >= since
            ).scalar()
            if user_high:
                user_score = user_high
                higher_count = db.query(func.count()).select_from(subquery).filter(
                    subquery.c.max_score > user_high
                ).scalar()
                user_rank = (higher_count or 0) + 1

        return LeaderboardResponse(
            entries=entries,
            total_count=total_count,
            page=page,
            page_size=page_size,
            user_rank=user_rank,
            user_score=user_score
        )

    def _get_user_rank(
        self,
        db: Session,
        user_id: UUID,
        game_mode: str,
        difficulty: str
    ) -> Tuple[Optional[int], Optional[int]]:
        """Get user's rank and high score"""
        # Get user's high score
        user_high = db.query(func.max(Score.score)).filter(
            Score.user_id == user_id,
            Score.game_mode == game_mode,
            Score.difficulty == difficulty
        ).scalar()

        if not user_high:
            return None, None

        # Count users with higher scores
        subquery = db.query(
            Score.user_id,
            func.max(Score.score).label('max_score')
        ).filter(
            Score.game_mode == game_mode,
            Score.difficulty == difficulty
        ).group_by(Score.user_id).subquery()

        higher_count = db.query(func.count()).select_from(subquery).filter(
            subquery.c.max_score > user_high
        ).scalar()

        return (higher_count or 0) + 1, user_high


leaderboard_service = LeaderboardService()
