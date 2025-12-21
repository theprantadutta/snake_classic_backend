from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
import logging

from ..services.firebase_service import firebase_service
from ..services.scheduler_service import scheduler_service
from ..models.notification import (
    IndividualNotificationRequest,
    TopicNotificationRequest,
    ScheduledNotificationRequest,
    NotificationResponse,
    TopicSubscriptionRequest,
    GameNotificationTemplates
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/send-individual", response_model=NotificationResponse)
async def send_individual_notification(request: IndividualNotificationRequest):
    """Send a notification to a specific user by FCM token."""
    try:
        result = await firebase_service.send_to_token(request)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send individual notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}"
        )


@router.post("/send-topic", response_model=NotificationResponse)
async def send_topic_notification(request: TopicNotificationRequest):
    """Send a notification to all subscribers of a topic."""
    try:
        result = await firebase_service.send_to_topic(request)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send topic notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}"
        )


@router.post("/send-multicast", response_model=NotificationResponse)
async def send_multicast_notification(
    notification_data: dict,
    tokens: List[str]
):
    """Send a notification to multiple FCM tokens."""
    try:
        from ..models.notification import NotificationRequest
        
        # Convert dict to NotificationRequest
        request = NotificationRequest(**notification_data)
        
        result = await firebase_service.send_multicast(request, tokens)
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to send multicast notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}"
        )


@router.post("/schedule")
async def schedule_notification(request: ScheduledNotificationRequest):
    """Schedule a notification for future delivery."""
    try:
        result = await scheduler_service.schedule_notification(request)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to schedule notification")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to schedule notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule notification: {str(e)}"
        )


@router.delete("/schedule/{job_id}")
async def cancel_scheduled_notification(job_id: str):
    """Cancel a scheduled notification."""
    try:
        result = await scheduler_service.cancel_scheduled_notification(job_id)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("message", "Job not found")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel scheduled notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel notification: {str(e)}"
        )


@router.get("/scheduled")
async def get_scheduled_notifications():
    """Get list of all scheduled notifications."""
    try:
        jobs = scheduler_service.get_scheduled_jobs()
        return {
            "success": True,
            "message": f"Found {len(jobs)} scheduled notifications",
            "jobs": jobs
        }
    
    except Exception as e:
        logger.error(f"Failed to get scheduled notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduled notifications: {str(e)}"
        )


@router.post("/game-templates/tournament-started")
async def send_tournament_started(tournament_name: str, tournament_id: str, topic: str = "tournaments"):
    """Send tournament started notification using game template."""
    try:
        notification = GameNotificationTemplates.tournament_started(tournament_name, tournament_id)
        
        request = TopicNotificationRequest(
            title=notification.title,
            body=notification.body,
            notification_type=notification.notification_type,
            priority=notification.priority,
            data=notification.data,
            route=notification.route,
            route_params=notification.route_params,
            topic=topic
        )
        
        result = await firebase_service.send_to_topic(request)
        return result
    
    except Exception as e:
        logger.error(f"Failed to send tournament notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send tournament notification: {str(e)}"
        )


@router.post("/game-templates/achievement-unlocked")
async def send_achievement_unlocked(
    achievement_name: str, 
    achievement_id: str, 
    fcm_token: str
):
    """Send achievement unlocked notification using game template."""
    try:
        notification = GameNotificationTemplates.achievement_unlocked(achievement_name, achievement_id)
        
        request = IndividualNotificationRequest(
            title=notification.title,
            body=notification.body,
            notification_type=notification.notification_type,
            priority=notification.priority,
            data=notification.data,
            route=notification.route,
            route_params=notification.route_params,
            fcm_token=fcm_token
        )
        
        result = await firebase_service.send_to_token(request)
        return result
    
    except Exception as e:
        logger.error(f"Failed to send achievement notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send achievement notification: {str(e)}"
        )


@router.post("/game-templates/friend-request")
async def send_friend_request(
    sender_name: str, 
    sender_id: str, 
    fcm_token: str
):
    """Send friend request notification using game template."""
    try:
        notification = GameNotificationTemplates.friend_request(sender_name, sender_id)
        
        request = IndividualNotificationRequest(
            title=notification.title,
            body=notification.body,
            notification_type=notification.notification_type,
            priority=notification.priority,
            data=notification.data,
            route=notification.route,
            route_params=notification.route_params,
            fcm_token=fcm_token
        )
        
        result = await firebase_service.send_to_token(request)
        return result
    
    except Exception as e:
        logger.error(f"Failed to send friend request notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send friend request notification: {str(e)}"
        )


@router.post("/game-templates/daily-challenge")
async def send_daily_challenge(topic: str = "daily_challenge"):
    """Send daily challenge notification using game template."""
    try:
        notification = GameNotificationTemplates.daily_challenge()
        
        request = TopicNotificationRequest(
            title=notification.title,
            body=notification.body,
            notification_type=notification.notification_type,
            priority=notification.priority,
            data=notification.data,
            route=notification.route,
            topic=topic
        )
        
        result = await firebase_service.send_to_topic(request)
        return result
    
    except Exception as e:
        logger.error(f"Failed to send daily challenge notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send daily challenge notification: {str(e)}"
        )


@router.post("/topics/subscribe")
async def subscribe_to_topic(request: TopicSubscriptionRequest):
    """Subscribe an FCM token to a topic."""
    try:
        result = await firebase_service.subscribe_to_topic(request.fcm_token, request.topic)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to subscribe to topic")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to subscribe to topic: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to subscribe to topic: {str(e)}"
        )


@router.post("/topics/unsubscribe")
async def unsubscribe_from_topic(request: TopicSubscriptionRequest):
    """Unsubscribe an FCM token from a topic."""
    try:
        result = await firebase_service.unsubscribe_from_topic(request.fcm_token, request.topic)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to unsubscribe from topic")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unsubscribe from topic: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unsubscribe from topic: {str(e)}"
        )