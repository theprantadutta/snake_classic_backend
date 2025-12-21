"""
API v1 routes aggregation
"""
from fastapi import APIRouter
from app.api.v1 import (
    auth, users, scores, leaderboard, achievements,
    social, tournaments, multiplayer, purchases, battle_pass, notifications
)

api_router = APIRouter()

# Authentication
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Users
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Scores
api_router.include_router(scores.router, tags=["scores"])

# Leaderboard
api_router.include_router(leaderboard.router, tags=["leaderboard"])

# Achievements
api_router.include_router(achievements.router, tags=["achievements"])

# Social/Friends
api_router.include_router(social.router, tags=["social"])

# Tournaments
api_router.include_router(tournaments.router, tags=["tournaments"])

# Multiplayer
api_router.include_router(multiplayer.router, tags=["multiplayer"])

# Purchases
api_router.include_router(purchases.router, tags=["purchases"])

# Battle Pass
api_router.include_router(battle_pass.router, tags=["battle-pass"])

# Notifications
api_router.include_router(notifications.router, tags=["notifications"])
