from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    """Types of notifications for Snake Classic game."""
    
    TOURNAMENT = "tournament"
    SOCIAL = "social" 
    ACHIEVEMENT = "achievement"
    DAILY_REMINDER = "daily_reminder"
    SPECIAL_EVENT = "special_event"


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class NotificationRequest(BaseModel):
    """Request model for sending notifications."""
    
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    notification_type: NotificationType = Field(..., description="Type of notification")
    priority: NotificationPriority = Field(NotificationPriority.NORMAL, description="Notification priority")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data payload")
    image_url: Optional[str] = Field(None, description="Optional image URL")
    
    # Routing information for deep linking
    route: Optional[str] = Field(None, description="App route to navigate to")
    route_params: Optional[Dict[str, Any]] = Field(None, description="Parameters for the route")


class IndividualNotificationRequest(NotificationRequest):
    """Request for sending notification to a specific user."""
    
    fcm_token: str = Field(..., description="FCM token of the target user")
    user_id: Optional[str] = Field(None, description="Optional user ID for tracking")


class TopicNotificationRequest(NotificationRequest):
    """Request for sending notification to a topic."""
    
    topic: str = Field(..., description="FCM topic name")
    condition: Optional[str] = Field(None, description="Optional condition for targeting")


class ScheduledNotificationRequest(NotificationRequest):
    """Request for scheduling a future notification."""
    
    scheduled_time: datetime = Field(..., description="When to send the notification")
    recipients: List[str] = Field(..., description="List of FCM tokens or topic names")
    recipient_type: str = Field("tokens", description="Type of recipients: 'tokens' or 'topics'")


class NotificationResponse(BaseModel):
    """Response model for notification operations."""
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    message_id: Optional[str] = Field(None, description="FCM message ID if successful")
    failure_count: Optional[int] = Field(None, description="Number of failed recipients")
    success_count: Optional[int] = Field(None, description="Number of successful recipients")
    errors: Optional[List[str]] = Field(None, description="Any error messages")


class TopicSubscriptionRequest(BaseModel):
    """Request for topic subscription operations."""
    
    fcm_token: str = Field(..., description="FCM token to subscribe/unsubscribe")
    topic: str = Field(..., description="Topic name")


class NotificationHistory(BaseModel):
    """Model for notification history tracking."""
    
    id: str = Field(..., description="Unique notification ID")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    notification_type: NotificationType = Field(..., description="Type of notification")
    priority: NotificationPriority = Field(..., description="Notification priority")
    sent_at: datetime = Field(..., description="When the notification was sent")
    recipient_count: int = Field(..., description="Number of recipients")
    success_count: int = Field(..., description="Number of successful deliveries")
    failure_count: int = Field(..., description="Number of failed deliveries")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data payload")


class GameNotificationTemplates:
    """Pre-defined notification templates for game events."""
    
    @staticmethod
    def tournament_started(tournament_name: str, tournament_id: str) -> NotificationRequest:
        return NotificationRequest(
            title="🏆 Tournament Started!",
            body=f"{tournament_name} has begun! Join now to compete!",
            notification_type=NotificationType.TOURNAMENT,
            priority=NotificationPriority.HIGH,
            route="tournament_detail",
            route_params={"tournament_id": tournament_id},
            data={"tournament_id": tournament_id, "action": "join"}
        )
    
    @staticmethod
    def achievement_unlocked(achievement_name: str, achievement_id: str) -> NotificationRequest:
        return NotificationRequest(
            title="🏆 Achievement Unlocked!",
            body=f"Congratulations! You've earned: {achievement_name}",
            notification_type=NotificationType.ACHIEVEMENT,
            priority=NotificationPriority.NORMAL,
            route="achievements",
            route_params={"achievement_id": achievement_id},
            data={"achievement_id": achievement_id, "action": "view"}
        )
    
    @staticmethod
    def friend_request(sender_name: str, sender_id: str) -> NotificationRequest:
        return NotificationRequest(
            title="👥 New Friend Request!",
            body=f"{sender_name} wants to be your friend",
            notification_type=NotificationType.SOCIAL,
            priority=NotificationPriority.NORMAL,
            route="friends_screen",
            route_params={"user_id": sender_id},
            data={"sender_id": sender_id, "action": "friend_request"}
        )
    
    @staticmethod
    def daily_challenge() -> NotificationRequest:
        return NotificationRequest(
            title="🐍 Daily Challenge Available!",
            body="Complete today's challenge and climb the leaderboard!",
            notification_type=NotificationType.DAILY_REMINDER,
            priority=NotificationPriority.LOW,
            route="home",
            data={"action": "daily_challenge"}
        )
    
    @staticmethod
    def special_event(event_name: str, event_description: str) -> NotificationRequest:
        return NotificationRequest(
            title=f"⭐ {event_name}",
            body=event_description,
            notification_type=NotificationType.SPECIAL_EVENT,
            priority=NotificationPriority.HIGH,
            route="home",
            data={"action": "special_event", "event": event_name}
        )