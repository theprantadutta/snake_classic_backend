"""
Notification management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, FCMToken
from app.utils.time_utils import utc_now
import logging

router = APIRouter(prefix="/notifications")
logger = logging.getLogger(__name__)


class TopicSubscriptionRequest(BaseModel):
    """Request for topic subscription"""
    fcm_token: str
    topic: str


class TopicSubscriptionResponse(BaseModel):
    """Response for topic subscription"""
    success: bool
    message: str
    topic: str


class TopicsListResponse(BaseModel):
    """Response containing list of subscribed topics"""
    success: bool
    topics: List[str]


@router.post("/topics/subscribe", response_model=TopicSubscriptionResponse)
async def subscribe_to_topic(
    request: TopicSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Subscribe an FCM token to a topic
    """
    try:
        # Find the token
        token_entry = db.query(FCMToken).filter(
            FCMToken.fcm_token == request.fcm_token,
            FCMToken.user_id == current_user.id
        ).first()

        if not token_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="FCM token not found for this user"
            )

        # Add topic to subscribed topics if not already there
        current_topics = token_entry.subscribed_topics or []
        if request.topic not in current_topics:
            current_topics.append(request.topic)
            token_entry.subscribed_topics = current_topics
            token_entry.updated_at = utc_now()
            db.commit()
            logger.info(f"User {current_user.id} subscribed to topic: {request.topic}")

        return {
            "success": True,
            "message": f"Subscribed to topic: {request.topic}",
            "topic": request.topic
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing to topic: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to subscribe to topic"
        )


@router.post("/topics/unsubscribe", response_model=TopicSubscriptionResponse)
async def unsubscribe_from_topic(
    request: TopicSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Unsubscribe an FCM token from a topic
    """
    try:
        # Find the token
        token_entry = db.query(FCMToken).filter(
            FCMToken.fcm_token == request.fcm_token,
            FCMToken.user_id == current_user.id
        ).first()

        if not token_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="FCM token not found for this user"
            )

        # Remove topic from subscribed topics
        current_topics = token_entry.subscribed_topics or []
        if request.topic in current_topics:
            current_topics.remove(request.topic)
            token_entry.subscribed_topics = current_topics
            token_entry.updated_at = utc_now()
            db.commit()
            logger.info(f"User {current_user.id} unsubscribed from topic: {request.topic}")

        return {
            "success": True,
            "message": f"Unsubscribed from topic: {request.topic}",
            "topic": request.topic
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsubscribing from topic: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsubscribe from topic"
        )


@router.get("/topics", response_model=TopicsListResponse)
async def get_subscribed_topics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all topics the user is subscribed to
    """
    try:
        # Get all tokens for this user and their topics
        tokens = db.query(FCMToken).filter(
            FCMToken.user_id == current_user.id
        ).all()

        all_topics = set()
        for token in tokens:
            if token.subscribed_topics:
                all_topics.update(token.subscribed_topics)

        return {
            "success": True,
            "topics": list(all_topics)
        }

    except Exception as e:
        logger.error(f"Error getting subscribed topics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscribed topics"
        )
