"""
Battle Pass service for managing battle pass progression
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.battle_pass import BattlePassSeason, UserBattlePassProgress
from app.models.user import UserPremiumContent
from app.schemas.battle_pass import (
    BattlePassReward,
    BattlePassLevel,
    BattlePassSeasonResponse,
    UserBattlePassProgressResponse,
)
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


def generate_levels_config() -> List[Dict]:
    """Generate default battle pass levels config"""
    levels = []
    for level in range(1, 101):
        xp_required = 100 + (level * 5)
        is_milestone = level % 10 == 0

        free_reward = None
        premium_reward = None

        # Free rewards every 5 levels
        if level % 5 == 0:
            free_reward = {
                "id": f"free_{level}",
                "name": f"Level {level} Free Reward",
                "description": f"Free reward for level {level}",
                "type": "xp" if level % 10 != 0 else "coins",
                "tier": "free",
                "quantity": 25 if level % 10 != 0 else 50,
                "icon": "" if level % 10 != 0 else ""
            }

        # Premium rewards every 3 levels
        if level % 3 == 0:
            reward_type = "skin" if level % 25 == 0 else "coins"
            premium_reward = {
                "id": f"premium_{level}",
                "name": f"Level {level} Premium Reward",
                "description": f"Premium reward for level {level}",
                "type": reward_type,
                "tier": "premium",
                "quantity": 1 if reward_type == "skin" else 100,
                "icon": "" if reward_type == "skin" else ""
            }

        levels.append({
            "level": level,
            "xp_required": xp_required,
            "free_reward": free_reward,
            "premium_reward": premium_reward,
            "is_milestone": is_milestone
        })

    return levels


class BattlePassService:
    """Service for battle pass operations"""

    def get_current_season(self, db: Session) -> Optional[BattlePassSeason]:
        """Get current active battle pass season"""
        now = utc_now()
        return db.query(BattlePassSeason).filter(
            BattlePassSeason.is_active == True,
            BattlePassSeason.start_date <= now,
            BattlePassSeason.end_date >= now
        ).first()

    def get_or_create_season(self, db: Session) -> BattlePassSeason:
        """Get current season or create a default one"""
        season = self.get_current_season(db)
        if season:
            return season

        # Create default season
        now = utc_now()
        season = BattlePassSeason(
            season_id="season_2025_01",
            name="Cosmic Serpent Season",
            description="Explore the cosmos with exclusive space-themed rewards",
            theme="cosmic",
            theme_color="#4B0082",
            start_date=now,
            end_date=now + timedelta(days=60),
            max_level=100,
            price=9.99,
            levels_config=generate_levels_config(),
            is_active=True
        )
        db.add(season)
        db.commit()
        db.refresh(season)
        return season

    def get_user_progress(
        self,
        db: Session,
        user_id: UUID,
        season: Optional[BattlePassSeason] = None
    ) -> UserBattlePassProgress:
        """Get or create user's battle pass progress"""
        if not season:
            season = self.get_or_create_season(db)

        progress = db.query(UserBattlePassProgress).filter(
            UserBattlePassProgress.user_id == user_id,
            UserBattlePassProgress.season_id == season.id
        ).first()

        if not progress:
            progress = UserBattlePassProgress(
                user_id=user_id,
                season_id=season.id,
                has_premium=False,
                current_level=1,
                current_xp=0,
                total_xp_earned=0,
                claimed_rewards=[]
            )
            db.add(progress)
            db.commit()
            db.refresh(progress)

        return progress

    def add_xp(
        self,
        db: Session,
        user_id: UUID,
        xp_amount: int
    ) -> Tuple[UserBattlePassProgress, int, int, bool, List[str]]:
        """
        Add XP to user's battle pass.
        Returns: (progress, old_level, new_level, leveled_up, rewards_unlocked)
        """
        season = self.get_or_create_season(db)
        progress = self.get_user_progress(db, user_id, season)

        old_level = progress.current_level
        progress.current_xp += xp_amount
        progress.total_xp_earned += xp_amount

        # Calculate new level
        levels_config = season.levels_config or generate_levels_config()
        total_xp = progress.current_xp
        new_level = 1
        xp_accumulated = 0

        for level_data in levels_config:
            level_xp = level_data["xp_required"]
            if total_xp >= xp_accumulated + level_xp:
                xp_accumulated += level_xp
                new_level = level_data["level"] + 1
            else:
                break

        new_level = min(new_level, season.max_level)
        progress.current_level = new_level

        db.commit()

        leveled_up = new_level > old_level
        rewards_unlocked = []

        if leveled_up:
            for lvl in range(old_level + 1, new_level + 1):
                level_config = next(
                    (l for l in levels_config if l["level"] == lvl),
                    None
                )
                if level_config:
                    if level_config.get("free_reward"):
                        rewards_unlocked.append(f"free_{lvl}")
                    if progress.has_premium and level_config.get("premium_reward"):
                        rewards_unlocked.append(f"premium_{lvl}")

        return progress, old_level, new_level, leveled_up, rewards_unlocked

    def claim_reward(
        self,
        db: Session,
        user_id: UUID,
        level: int,
        tier: str
    ) -> Tuple[bool, Optional[BattlePassReward], str]:
        """
        Claim a battle pass reward.
        Returns: (success, reward, message)
        """
        season = self.get_or_create_season(db)
        progress = self.get_user_progress(db, user_id, season)

        # Check level requirement
        if progress.current_level < level:
            return False, None, f"Level {level} not reached yet"

        # Check premium requirement
        if tier == "premium" and not progress.has_premium:
            return False, None, "Premium Battle Pass required"

        # Check if already claimed
        reward_key = f"{level}_{tier}"
        if reward_key in (progress.claimed_rewards or []):
            return False, None, "Reward already claimed"

        # Find reward
        levels_config = season.levels_config or generate_levels_config()
        level_config = next(
            (l for l in levels_config if l["level"] == level),
            None
        )

        if not level_config:
            return False, None, "Level not found"

        reward_data = (
            level_config.get("free_reward") if tier == "free"
            else level_config.get("premium_reward")
        )

        if not reward_data:
            return False, None, f"No {tier} reward at level {level}"

        # Mark as claimed
        claimed = list(progress.claimed_rewards or [])
        claimed.append(reward_key)
        progress.claimed_rewards = claimed

        db.commit()

        reward = BattlePassReward(**reward_data)
        return True, reward, f"Claimed {reward.name}"

    def purchase_premium(
        self,
        db: Session,
        user_id: UUID
    ) -> Tuple[bool, str]:
        """
        Activate premium battle pass for user.
        Returns: (success, message)
        """
        season = self.get_or_create_season(db)
        progress = self.get_user_progress(db, user_id, season)

        if progress.has_premium:
            return False, "Premium already active"

        progress.has_premium = True
        progress.purchase_date = utc_now()

        # Also update premium content
        premium = db.query(UserPremiumContent).filter(
            UserPremiumContent.user_id == user_id
        ).first()

        if premium:
            premium.battle_pass_active = True
            premium.battle_pass_expires_at = season.end_date

        db.commit()

        return True, "Premium Battle Pass activated"

    def get_progress_response(
        self,
        progress: UserBattlePassProgress,
        season: BattlePassSeason
    ) -> UserBattlePassProgressResponse:
        """Convert progress to response format"""
        levels_config = season.levels_config or generate_levels_config()

        # Calculate XP to next level
        next_level_xp = 0
        progress_percent = 100.0

        if progress.current_level < season.max_level:
            current_level_config = next(
                (l for l in levels_config if l["level"] == progress.current_level),
                None
            )
            if current_level_config:
                # Calculate XP into current level
                xp_before_level = sum(
                    l["xp_required"] for l in levels_config
                    if l["level"] < progress.current_level
                )
                xp_in_level = progress.current_xp - xp_before_level
                next_level_xp = current_level_config["xp_required"]
                progress_percent = min(100.0, (xp_in_level / next_level_xp) * 100)

        return UserBattlePassProgressResponse(
            id=progress.id,
            user_id=progress.user_id,
            season_id=progress.season_id,
            has_premium=progress.has_premium,
            current_level=progress.current_level,
            current_xp=progress.current_xp,
            total_xp_earned=progress.total_xp_earned,
            purchase_date=progress.purchase_date,
            claimed_rewards=progress.claimed_rewards or [],
            next_level_xp=next_level_xp,
            progress_percent=round(progress_percent, 2)
        )


battle_pass_service = BattlePassService()
