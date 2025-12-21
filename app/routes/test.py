from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import logging

from ..services.firebase_service import firebase_service
from ..models.notification import (
    IndividualNotificationRequest,
    TopicNotificationRequest,
    NotificationType,
    NotificationPriority
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/test", tags=["testing"])


class TestNotificationRequest(BaseModel):
    """Simple test notification request."""
    fcm_token: str
    title: Optional[str] = "🐍 Test Notification"
    body: Optional[str] = "This is a test notification from Snake Classic backend!"
    route: Optional[str] = "home"


class TopicTestRequest(BaseModel):
    """Test notification for topic."""
    topic: str
    title: Optional[str] = "📢 Topic Test"
    body: Optional[str] = "This is a test notification sent to a topic!"


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Snake Classic Notification Backend is running",
        "service": "notification-backend",
        "version": "1.0.0"
    }


@router.post("/send-test-notification")
async def send_test_notification(request: TestNotificationRequest):
    """Send a test notification to verify the system is working."""
    try:
        notification_request = IndividualNotificationRequest(
            title=request.title,
            body=request.body,
            notification_type=NotificationType.SPECIAL_EVENT,
            priority=NotificationPriority.NORMAL,
            fcm_token=request.fcm_token,
            route=request.route,
            data={
                "test": "true",
                "source": "backend",
                "timestamp": str(datetime.utcnow())
            }
        )
        
        result = await firebase_service.send_to_token(notification_request)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to send test notification: {result.message}"
            )
        
        return {
            "success": True,
            "message": "Test notification sent successfully!",
            "details": {
                "message_id": result.message_id,
                "token": request.fcm_token[:10] + "...",  # Partial token for security
                "title": request.title,
                "body": request.body
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send test notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test notification: {str(e)}"
        )


@router.post("/send-topic-test")
async def send_topic_test_notification(request: TopicTestRequest):
    """Send a test notification to a topic."""
    try:
        notification_request = TopicNotificationRequest(
            title=request.title,
            body=request.body,
            notification_type=NotificationType.SPECIAL_EVENT,
            priority=NotificationPriority.NORMAL,
            topic=request.topic,
            data={
                "test": "true",
                "source": "backend",
                "topic": request.topic,
                "timestamp": str(datetime.utcnow())
            }
        )
        
        result = await firebase_service.send_to_topic(notification_request)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to send topic test notification: {result.message}"
            )
        
        return {
            "success": True,
            "message": f"Test notification sent to topic '{request.topic}' successfully!",
            "details": {
                "message_id": result.message_id,
                "topic": request.topic,
                "title": request.title,
                "body": request.body
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send topic test notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send topic test notification: {str(e)}"
        )


@router.post("/validate-token")
async def validate_fcm_token(fcm_token: str):
    """Validate if an FCM token is still valid."""
    try:
        is_valid = await firebase_service.validate_token(fcm_token)
        
        return {
            "success": True,
            "message": "Token validation completed",
            "valid": is_valid,
            "token": fcm_token[:10] + "..."  # Partial token for security
        }
    
    except Exception as e:
        logger.error(f"Failed to validate FCM token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate token: {str(e)}"
        )


@router.get("/firebase-status")
async def get_firebase_status():
    """Check Firebase service status."""
    try:
        # Check if Firebase is initialized
        is_initialized = firebase_service._initialized
        
        return {
            "success": True,
            "message": "Firebase status check completed",
            "firebase_initialized": is_initialized,
            "project_id": "snake-classic-2a376" if is_initialized else "Not available"
        }
    
    except Exception as e:
        logger.error(f"Failed to check Firebase status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check Firebase status: {str(e)}"
        )


@router.post("/quick-game-notification")
async def send_quick_game_notification(
    fcm_token: str,
    message_type: str = "achievement"
):
    """Send a quick game-specific notification for testing."""
    try:
        notifications = {
            "achievement": {
                "title": "🏆 Achievement Unlocked!",
                "body": "You've earned the 'First Victory' achievement!",
                "route": "achievements"
            },
            "tournament": {
                "title": "🏆 Tournament Alert!",
                "body": "Snake Masters Championship is starting in 5 minutes!",
                "route": "tournament_detail"
            },
            "friend": {
                "title": "👥 New Friend Request!",
                "body": "SnakePlayer123 wants to be your friend",
                "route": "friends_screen"
            },
            "daily": {
                "title": "🐍 Daily Challenge!",
                "body": "Your daily challenge is ready! Can you beat yesterday's score?",
                "route": "home"
            }
        }
        
        if message_type not in notifications:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid message type. Available types: {list(notifications.keys())}"
            )
        
        notification_data = notifications[message_type]
        
        notification_request = IndividualNotificationRequest(
            title=notification_data["title"],
            body=notification_data["body"],
            notification_type=NotificationType.SPECIAL_EVENT,
            priority=NotificationPriority.NORMAL,
            fcm_token=fcm_token,
            route=notification_data["route"],
            data={
                "test": "true",
                "message_type": message_type,
                "source": "quick_test"
            }
        )
        
        result = await firebase_service.send_to_token(notification_request)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to send quick notification: {result.message}"
            )
        
        return {
            "success": True,
            "message": f"Quick {message_type} notification sent successfully!",
            "details": {
                "message_id": result.message_id,
                "type": message_type,
                "title": notification_data["title"],
                "body": notification_data["body"]
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send quick game notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send quick notification: {str(e)}"
        )


# Import datetime for timestamps
from datetime import datetime