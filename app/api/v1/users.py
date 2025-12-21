"""
User management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from uuid import UUID
import re
from app.database import get_db
from app.schemas.user import (
    UserResponse,
    UserProfileResponse,
    UserUpdate,
    UserPreferencesUpdate,
    UserPreferencesResponse,
    UsernameCheckRequest,
    UsernameCheckResponse,
    UserSearchResponse,
)
from app.core.dependencies import get_current_user, get_optional_current_user
from app.models.user import User, UserPreferences, FCMToken
from app.utils.time_utils import utc_now
import logging
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

# Reserved usernames that cannot be used
RESERVED_USERNAMES = {
    'admin', 'administrator', 'mod', 'moderator', 'system', 'bot',
    'snake', 'classic', 'game', 'support', 'help', 'official',
    'null', 'undefined', 'anonymous', 'guest', 'user', 'player'
}


def validate_username(username: str) -> tuple[bool, str]:
    """
    Validate username format

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 20:
        return False, "Username must be at most 20 characters"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    if username.lower() in RESERVED_USERNAMES:
        return False, "This username is reserved"
    return True, ""


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's full profile including preferences and premium content
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile
    """
    # Validate username if being updated
    if update_data.username is not None:
        is_valid, error_msg = validate_username(update_data.username)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Check if username is taken
        existing = db.query(User).filter(
            User.username == update_data.username,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(current_user, field, value)

    current_user.updated_at = utc_now()
    db.commit()
    db.refresh(current_user)

    logger.info(f"Updated profile for user: {current_user.id}")
    return current_user


@router.get("/me/preferences", response_model=UserPreferencesResponse)
async def get_my_preferences(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's preferences
    """
    if not current_user.preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preferences not found"
        )
    return current_user.preferences


@router.put("/me/preferences", response_model=UserPreferencesResponse)
async def update_my_preferences(
    update_data: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's preferences
    """
    if not current_user.preferences:
        # Create preferences if they don't exist
        preferences = UserPreferences(user_id=current_user.id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
        current_user.preferences = preferences

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(current_user.preferences, field, value)

    current_user.preferences.updated_at = utc_now()
    db.commit()
    db.refresh(current_user.preferences)

    return current_user.preferences


@router.post("/username/check", response_model=UsernameCheckResponse)
async def check_username_availability(
    request: UsernameCheckRequest,
    db: Session = Depends(get_db)
):
    """
    Check if a username is available
    """
    username = request.username.lower()

    # Validate format
    is_valid, error_msg = validate_username(username)
    if not is_valid:
        return {
            "username": request.username,
            "available": False,
            "message": error_msg
        }

    # Check if taken
    existing = db.query(User).filter(func.lower(User.username) == username).first()
    if existing:
        return {
            "username": request.username,
            "available": False,
            "message": "Username already taken"
        }

    return {
        "username": request.username,
        "available": True,
        "message": "Username is available"
    }


@router.put("/username")
async def set_username(
    request: UsernameCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set or change current user's username
    """
    username = request.username

    # Validate format
    is_valid, error_msg = validate_username(username)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Check if taken
    existing = db.query(User).filter(
        func.lower(User.username) == username.lower(),
        User.id != current_user.id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken"
        )

    current_user.username = username
    current_user.updated_at = utc_now()
    db.commit()
    db.refresh(current_user)

    return {
        "success": True,
        "username": current_user.username,
        "message": "Username set successfully"
    }


@router.get("/{user_id}", response_model=UserSearchResponse)
async def get_user_profile(
    user_id: UUID,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a user's public profile by ID
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if profile is public or if it's the current user
    if not user.is_public and (not current_user or current_user.id != user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This profile is private"
        )

    return user


@router.get("/by-username/{username}", response_model=UserSearchResponse)
async def get_user_by_username(
    username: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a user's profile by username
    """
    user = db.query(User).filter(func.lower(User.username) == username.lower()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if profile is public or if it's the current user
    if not user.is_public and (not current_user or current_user.id != user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This profile is private"
        )

    return user


@router.get("/search/", response_model=List[UserSearchResponse])
async def search_users(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search for users by username or display name

    Only returns public profiles.
    """
    search_query = f"%{q}%"

    users = db.query(User).filter(
        User.is_public == True,
        User.is_active == True,
        or_(
            User.username.ilike(search_query),
            User.display_name.ilike(search_query)
        )
    ).order_by(
        User.level.desc()
    ).offset(offset).limit(limit).all()

    return users


class FCMTokenRegisterRequest(BaseModel):
    """Request for registering FCM token"""
    fcm_token: str
    platform: str = "flutter"


class FCMTokenRegisterResponse(BaseModel):
    """Response for FCM token registration"""
    success: bool
    message: str


@router.post("/register-token", response_model=FCMTokenRegisterResponse)
async def register_fcm_token(
    request: FCMTokenRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Register or update FCM token for push notifications
    """
    try:
        # Check if token already exists for this user
        existing_token = db.query(FCMToken).filter(
            FCMToken.fcm_token == request.fcm_token
        ).first()

        if existing_token:
            # Update existing token's user if different
            if existing_token.user_id != current_user.id:
                existing_token.user_id = current_user.id
                existing_token.platform = request.platform
                existing_token.updated_at = utc_now()
                db.commit()
                logger.info(f"FCM token transferred to user: {current_user.id}")
            return {
                "success": True,
                "message": "FCM token already registered"
            }

        # Create new token entry
        new_token = FCMToken(
            user_id=current_user.id,
            fcm_token=request.fcm_token,
            platform=request.platform,
            subscribed_topics=[]
        )
        db.add(new_token)
        db.commit()

        logger.info(f"FCM token registered for user: {current_user.id}")
        return {
            "success": True,
            "message": "FCM token registered successfully"
        }

    except Exception as e:
        logger.error(f"Error registering FCM token: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register FCM token"
        )
