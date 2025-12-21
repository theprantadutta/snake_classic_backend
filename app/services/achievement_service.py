"""
Achievement service for tracking and managing achievements
"""
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.achievement import Achievement, UserAchievement
from app.models.user import User
from app.schemas.achievement import (
    AchievementProgressUpdate,
    AchievementProgressResponse,
    UserAchievementSummary,
    UserAchievementResponse,
    AchievementResponse,
)
from app.utils.time_utils import utc_now


# Default achievements to seed
DEFAULT_ACHIEVEMENTS = [
    # Score achievements
    {"achievement_id": "first_bite", "name": "First Bite", "description": "Score your first point", "category": "score", "tier": "bronze", "requirement_value": 1, "xp_reward": 10, "coin_reward": 5},
    {"achievement_id": "getting_started", "name": "Getting Started", "description": "Score 100 points", "category": "score", "tier": "bronze", "requirement_value": 100, "xp_reward": 25, "coin_reward": 10},
    {"achievement_id": "high_scorer", "name": "High Scorer", "description": "Score 500 points in a single game", "category": "score", "tier": "silver", "requirement_value": 500, "xp_reward": 50, "coin_reward": 25},
    {"achievement_id": "master_scorer", "name": "Master Scorer", "description": "Score 1000 points in a single game", "category": "score", "tier": "gold", "requirement_value": 1000, "xp_reward": 100, "coin_reward": 50},
    {"achievement_id": "legendary_scorer", "name": "Legendary Scorer", "description": "Score 2000 points in a single game", "category": "score", "tier": "platinum", "requirement_value": 2000, "xp_reward": 200, "coin_reward": 100},

    # Food achievements
    {"achievement_id": "snack_time", "name": "Snack Time", "description": "Eat 10 foods total", "category": "food", "tier": "bronze", "requirement_value": 10, "xp_reward": 10, "coin_reward": 5},
    {"achievement_id": "hungry_snake", "name": "Hungry Snake", "description": "Eat 100 foods total", "category": "food", "tier": "silver", "requirement_value": 100, "xp_reward": 50, "coin_reward": 25},
    {"achievement_id": "bottomless_pit", "name": "Bottomless Pit", "description": "Eat 500 foods total", "category": "food", "tier": "gold", "requirement_value": 500, "xp_reward": 100, "coin_reward": 50},
    {"achievement_id": "food_champion", "name": "Food Champion", "description": "Eat 1000 foods total", "category": "food", "tier": "platinum", "requirement_value": 1000, "xp_reward": 200, "coin_reward": 100},

    # Games played achievements
    {"achievement_id": "first_game", "name": "First Game", "description": "Play your first game", "category": "games", "tier": "bronze", "requirement_value": 1, "xp_reward": 10, "coin_reward": 5},
    {"achievement_id": "regular_player", "name": "Regular Player", "description": "Play 10 games", "category": "games", "tier": "bronze", "requirement_value": 10, "xp_reward": 25, "coin_reward": 10},
    {"achievement_id": "dedicated_player", "name": "Dedicated Player", "description": "Play 50 games", "category": "games", "tier": "silver", "requirement_value": 50, "xp_reward": 50, "coin_reward": 25},
    {"achievement_id": "snake_enthusiast", "name": "Snake Enthusiast", "description": "Play 100 games", "category": "games", "tier": "gold", "requirement_value": 100, "xp_reward": 100, "coin_reward": 50},
    {"achievement_id": "snake_addict", "name": "Snake Addict", "description": "Play 500 games", "category": "games", "tier": "platinum", "requirement_value": 500, "xp_reward": 250, "coin_reward": 125},

    # Duration achievements
    {"achievement_id": "survivor", "name": "Survivor", "description": "Survive for 60 seconds", "category": "survival", "tier": "bronze", "requirement_value": 60, "xp_reward": 15, "coin_reward": 5},
    {"achievement_id": "endurance", "name": "Endurance", "description": "Survive for 2 minutes", "category": "survival", "tier": "silver", "requirement_value": 120, "xp_reward": 30, "coin_reward": 15},
    {"achievement_id": "marathon", "name": "Marathon", "description": "Survive for 5 minutes", "category": "survival", "tier": "gold", "requirement_value": 300, "xp_reward": 75, "coin_reward": 35},

    # Social achievements
    {"achievement_id": "social_butterfly", "name": "Social Butterfly", "description": "Add your first friend", "category": "social", "tier": "bronze", "requirement_value": 1, "xp_reward": 20, "coin_reward": 10},
    {"achievement_id": "popular", "name": "Popular", "description": "Have 10 friends", "category": "social", "tier": "silver", "requirement_value": 10, "xp_reward": 50, "coin_reward": 25},

    # Tournament achievements
    {"achievement_id": "competitor", "name": "Competitor", "description": "Join your first tournament", "category": "tournament", "tier": "bronze", "requirement_value": 1, "xp_reward": 25, "coin_reward": 10},
    {"achievement_id": "tournament_regular", "name": "Tournament Regular", "description": "Join 10 tournaments", "category": "tournament", "tier": "silver", "requirement_value": 10, "xp_reward": 75, "coin_reward": 35},
]


class AchievementService:
    """Service for achievement operations"""

    def seed_achievements(self, db: Session) -> int:
        """Seed default achievements if they don't exist"""
        created = 0
        for ach_data in DEFAULT_ACHIEVEMENTS:
            existing = db.query(Achievement).filter(
                Achievement.achievement_id == ach_data["achievement_id"]
            ).first()
            if not existing:
                achievement = Achievement(**ach_data)
                db.add(achievement)
                created += 1
        if created > 0:
            db.commit()
        return created

    def get_all_achievements(self, db: Session) -> List[Achievement]:
        """Get all available achievements"""
        return db.query(Achievement).all()

    def get_achievement_by_id(self, db: Session, achievement_id: str) -> Optional[Achievement]:
        """Get achievement by string ID"""
        return db.query(Achievement).filter(
            Achievement.achievement_id == achievement_id
        ).first()

    def get_user_achievements(self, db: Session, user_id: UUID) -> List[UserAchievement]:
        """Get all user achievements with progress"""
        return db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id
        ).all()

    def get_user_achievement_summary(
        self,
        db: Session,
        user_id: UUID
    ) -> UserAchievementSummary:
        """Get summary of user's achievements"""
        all_achievements = self.get_all_achievements(db)
        user_achievements = {
            ua.achievement_id: ua
            for ua in self.get_user_achievements(db, user_id)
        }

        achievement_responses = []
        unlocked_count = 0
        total_xp = 0
        total_coins = 0

        for ach in all_achievements:
            user_ach = user_achievements.get(ach.id)
            if user_ach:
                achievement_responses.append(UserAchievementResponse(
                    id=user_ach.id,
                    achievement=AchievementResponse.model_validate(ach),
                    current_progress=user_ach.current_progress,
                    is_unlocked=user_ach.is_unlocked,
                    unlocked_at=user_ach.unlocked_at,
                    created_at=user_ach.created_at
                ))
                if user_ach.is_unlocked:
                    unlocked_count += 1
                    total_xp += ach.xp_reward or 0
                    total_coins += ach.coin_reward or 0
            else:
                # Create placeholder for achievements not yet tracked
                achievement_responses.append(UserAchievementResponse(
                    id=ach.id,  # Use achievement ID as placeholder
                    achievement=AchievementResponse.model_validate(ach),
                    current_progress=0,
                    is_unlocked=False,
                    unlocked_at=None,
                    created_at=utc_now()
                ))

        completion = (unlocked_count / len(all_achievements) * 100) if all_achievements else 0

        return UserAchievementSummary(
            total_achievements=len(all_achievements),
            unlocked_count=unlocked_count,
            locked_count=len(all_achievements) - unlocked_count,
            total_xp_earned=total_xp,
            total_coins_earned=total_coins,
            completion_percentage=round(completion, 2),
            achievements=achievement_responses
        )

    def update_progress(
        self,
        db: Session,
        user_id: UUID,
        achievement_id: str,
        progress_increment: int = 1
    ) -> AchievementProgressResponse:
        """Update progress for an achievement"""
        # Get achievement
        achievement = self.get_achievement_by_id(db, achievement_id)
        if not achievement:
            raise ValueError(f"Achievement {achievement_id} not found")

        # Get or create user achievement
        user_ach = db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement.id
        ).first()

        previous_progress = 0
        newly_unlocked = False

        if not user_ach:
            user_ach = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id,
                current_progress=0,
                is_unlocked=False
            )
            db.add(user_ach)

        previous_progress = user_ach.current_progress
        user_ach.current_progress += progress_increment

        # Check if achievement is now unlocked
        if not user_ach.is_unlocked and user_ach.current_progress >= achievement.requirement_value:
            user_ach.is_unlocked = True
            user_ach.unlocked_at = utc_now()
            newly_unlocked = True

        db.commit()

        return AchievementProgressResponse(
            achievement_id=achievement_id,
            previous_progress=previous_progress,
            current_progress=user_ach.current_progress,
            requirement=achievement.requirement_value,
            is_unlocked=user_ach.is_unlocked,
            newly_unlocked=newly_unlocked,
            xp_reward=achievement.xp_reward if newly_unlocked else None,
            coin_reward=achievement.coin_reward if newly_unlocked else None
        )

    def set_progress(
        self,
        db: Session,
        user_id: UUID,
        achievement_id: str,
        progress_value: int
    ) -> AchievementProgressResponse:
        """Set absolute progress value for an achievement"""
        achievement = self.get_achievement_by_id(db, achievement_id)
        if not achievement:
            raise ValueError(f"Achievement {achievement_id} not found")

        user_ach = db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement.id
        ).first()

        previous_progress = 0
        newly_unlocked = False

        if not user_ach:
            user_ach = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id,
                current_progress=0,
                is_unlocked=False
            )
            db.add(user_ach)

        previous_progress = user_ach.current_progress

        # Only update if new value is higher
        if progress_value > user_ach.current_progress:
            user_ach.current_progress = progress_value

        if not user_ach.is_unlocked and user_ach.current_progress >= achievement.requirement_value:
            user_ach.is_unlocked = True
            user_ach.unlocked_at = utc_now()
            newly_unlocked = True

        db.commit()

        return AchievementProgressResponse(
            achievement_id=achievement_id,
            previous_progress=previous_progress,
            current_progress=user_ach.current_progress,
            requirement=achievement.requirement_value,
            is_unlocked=user_ach.is_unlocked,
            newly_unlocked=newly_unlocked,
            xp_reward=achievement.xp_reward if newly_unlocked else None,
            coin_reward=achievement.coin_reward if newly_unlocked else None
        )

    def check_score_achievements(
        self,
        db: Session,
        user_id: UUID,
        score: int,
        foods_eaten: int,
        duration: int
    ) -> List[AchievementProgressResponse]:
        """Check and update achievements after a game"""
        unlocked = []

        # Score achievements
        score_achievements = ["first_bite", "getting_started", "high_scorer", "master_scorer", "legendary_scorer"]
        for ach_id in score_achievements:
            result = self.set_progress(db, user_id, ach_id, score)
            if result.newly_unlocked:
                unlocked.append(result)

        # Duration achievements
        duration_achievements = ["survivor", "endurance", "marathon"]
        for ach_id in duration_achievements:
            result = self.set_progress(db, user_id, ach_id, duration)
            if result.newly_unlocked:
                unlocked.append(result)

        # Games played - increment
        result = self.update_progress(db, user_id, "first_game", 1)
        if result.newly_unlocked:
            unlocked.append(result)
        self.update_progress(db, user_id, "regular_player", 1)
        self.update_progress(db, user_id, "dedicated_player", 1)
        self.update_progress(db, user_id, "snake_enthusiast", 1)
        self.update_progress(db, user_id, "snake_addict", 1)

        # Food achievements - increment
        if foods_eaten > 0:
            self.update_progress(db, user_id, "snack_time", foods_eaten)
            self.update_progress(db, user_id, "hungry_snake", foods_eaten)
            self.update_progress(db, user_id, "bottomless_pit", foods_eaten)
            self.update_progress(db, user_id, "food_champion", foods_eaten)

        return unlocked


achievement_service = AchievementService()
