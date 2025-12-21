from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from ..services.firebase_service import firebase_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["user-management"])


class UserTokenRegistration(BaseModel):
    """Model for registering user FCM tokens."""
    fcm_token: str
    user_id: str
    username: Optional[str] = None
    platform: Optional[str] = "flutter"
    registered_at: Optional[str] = None


class UserTopicsResponse(BaseModel):
    """Response model for user's subscribed topics."""
    user_id: str
    topics: list[str]


# In-memory storage for demo purposes
# In production, use a proper database
user_tokens: Dict[str, UserTokenRegistration] = {}
user_topics: Dict[str, list[str]] = {}


@router.post("/register-token")
async def register_user_token(registration: UserTokenRegistration):
    """Register or update a user's FCM token."""
    try:
        # Validate the token
        is_valid = await firebase_service.validate_token(registration.fcm_token)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid FCM token"
            )
        
        # Store the registration (in production, save to database)
        user_tokens[registration.user_id] = registration
        
        logger.info(f"FCM token registered for user {registration.user_id}")
        
        return {
            "success": True,
            "message": "FCM token registered successfully",
            "user_id": registration.user_id,
            "username": registration.username,
            "registered_at": registration.registered_at or datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register FCM token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register token: {str(e)}"
        )


@router.get("/token/{user_id}")
async def get_user_token(user_id: str):
    """Get a user's registered FCM token."""
    if user_id not in user_tokens:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User token not found"
        )
    
    registration = user_tokens[user_id]
    
    return {
        "success": True,
        "user_id": user_id,
        "username": registration.username,
        "platform": registration.platform,
        "token": registration.fcm_token[:10] + "...",  # Partial token for security
        "registered_at": registration.registered_at
    }


@router.delete("/token/{user_id}")
async def delete_user_token(user_id: str):
    """Delete a user's FCM token registration."""
    if user_id not in user_tokens:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User token not found"
        )
    
    del user_tokens[user_id]
    
    # Also remove from topics
    if user_id in user_topics:
        del user_topics[user_id]
    
    logger.info(f"FCM token deleted for user {user_id}")
    
    return {
        "success": True,
        "message": f"Token registration deleted for user {user_id}"
    }


@router.get("/topics/{user_id}")
async def get_user_topics(user_id: str):
    """Get topics a user is subscribed to."""
    topics = user_topics.get(user_id, [])
    
    return {
        "success": True,
        "user_id": user_id,
        "topics": topics,
        "topic_count": len(topics)
    }


@router.post("/topics/{user_id}/subscribe")
async def subscribe_user_to_topics(user_id: str, topics: list[str]):
    """Subscribe a user to multiple topics."""
    if user_id not in user_tokens:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User token not found. Register token first."
        )
    
    try:
        registration = user_tokens[user_id]
        
        # Subscribe to topics via Firebase
        result = await firebase_service.subscribe_to_topic(
            tokens=registration.fcm_token,
            topic=topics[0] if topics else ""  # Firebase API subscribes one topic at a time
        )
        
        # Update local tracking
        if user_id not in user_topics:
            user_topics[user_id] = []
        
        for topic in topics:
            if topic not in user_topics[user_id]:
                user_topics[user_id].append(topic)
        
        logger.info(f"User {user_id} subscribed to topics: {topics}")
        
        return {
            "success": True,
            "message": f"Subscribed to {len(topics)} topics",
            "user_id": user_id,
            "topics": topics,
            "total_topics": len(user_topics[user_id])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to subscribe user to topics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to subscribe to topics: {str(e)}"
        )


@router.post("/topics/{user_id}/unsubscribe")
async def unsubscribe_user_from_topics(user_id: str, topics: list[str]):
    """Unsubscribe a user from multiple topics."""
    if user_id not in user_tokens:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User token not found"
        )
    
    try:
        registration = user_tokens[user_id]
        
        # Unsubscribe from topics via Firebase
        for topic in topics:
            await firebase_service.unsubscribe_from_topic(
                tokens=registration.fcm_token,
                topic=topic
            )
        
        # Update local tracking
        if user_id in user_topics:
            for topic in topics:
                if topic in user_topics[user_id]:
                    user_topics[user_id].remove(topic)
        
        logger.info(f"User {user_id} unsubscribed from topics: {topics}")
        
        return {
            "success": True,
            "message": f"Unsubscribed from {len(topics)} topics",
            "user_id": user_id,
            "topics": topics,
            "remaining_topics": len(user_topics.get(user_id, []))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unsubscribe user from topics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unsubscribe from topics: {str(e)}"
        )


@router.get("/")
async def list_registered_users():
    """List all registered users (for admin/debugging)."""
    return {
        "success": True,
        "message": f"Found {len(user_tokens)} registered users",
        "users": [
            {
                "user_id": user_id,
                "username": reg.username,
                "platform": reg.platform,
                "registered_at": reg.registered_at,
                "topics_count": len(user_topics.get(user_id, []))
            }
            for user_id, reg in user_tokens.items()
        ],
        "total_users": len(user_tokens)
    }