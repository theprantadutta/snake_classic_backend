"""
Database models for Snake Classic Backend

All models should be imported here for Alembic to detect them.
"""
from app.models.user import User, UserPreferences, FCMToken, UserPremiumContent
from app.models.score import Score, GameReplay
from app.models.achievement import Achievement, UserAchievement
from app.models.social import Friendship
from app.models.tournament import Tournament, TournamentEntry
from app.models.multiplayer import MultiplayerGame, MultiplayerPlayer
from app.models.battle_pass import BattlePassSeason, UserBattlePassProgress
from app.models.purchase import Purchase, NotificationHistory, ScheduledJob

__all__ = [
    # User
    "User",
    "UserPreferences",
    "FCMToken",
    "UserPremiumContent",
    # Score
    "Score",
    "GameReplay",
    # Achievement
    "Achievement",
    "UserAchievement",
    # Social
    "Friendship",
    # Tournament
    "Tournament",
    "TournamentEntry",
    # Multiplayer
    "MultiplayerGame",
    "MultiplayerPlayer",
    # Battle Pass
    "BattlePassSeason",
    "UserBattlePassProgress",
    # Purchase
    "Purchase",
    "NotificationHistory",
    "ScheduledJob",
]