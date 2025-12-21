import json
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, messaging
from ..core.config import settings
from ..models.notification import (
    NotificationRequest, 
    IndividualNotificationRequest, 
    TopicNotificationRequest,
    NotificationResponse,
    NotificationPriority
)

logger = logging.getLogger(__name__)


class FirebaseService:
    """Service for managing Firebase Cloud Messaging operations."""
    
    def __init__(self):
        self._initialized = False
        self._app = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK."""
        try:
            if not firebase_admin._apps:
                # Load service account credentials
                cred = credentials.Certificate(settings.google_application_credentials)
                self._app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                self._app = firebase_admin._apps[0]
                logger.info("Using existing Firebase Admin SDK instance")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            raise
    
    def _create_message(
        self, 
        notification_data: NotificationRequest,
        token: Optional[str] = None,
        topic: Optional[str] = None,
        condition: Optional[str] = None
    ) -> messaging.Message:
        """Create FCM message from notification data."""
        
        # Create notification object
        notification = messaging.Notification(
            title=notification_data.title,
            body=notification_data.body,
            image=notification_data.image_url
        )
        
        # Prepare data payload
        data = {}
        if notification_data.data:
            data.update(notification_data.data)
        
        # Add routing information
        if notification_data.route:
            data["route"] = notification_data.route
        
        if notification_data.route_params:
            data["route_params"] = json.dumps(notification_data.route_params)
        
        # Add notification metadata
        data.update({
            "notification_type": notification_data.notification_type.value,
            "priority": notification_data.priority.value,
            "sent_at": datetime.utcnow().isoformat()
        })
        
        # Convert all data values to strings (FCM requirement)
        data = {k: str(v) for k, v in data.items()}
        
        # Create Android-specific config
        android_config = messaging.AndroidConfig(
            priority="high" if notification_data.priority == NotificationPriority.HIGH else "normal",
            notification=messaging.AndroidNotification(
                title=notification_data.title,
                body=notification_data.body,
                icon="@mipmap/ic_launcher",
                color="#4CAF50",  # Snake Classic brand color
                sound="default",
                channel_id="snake_classic_notifications"
            )
        )
        
        # Create iOS-specific config
        ios_config = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=notification_data.title,
                        body=notification_data.body
                    ),
                    badge=1,
                    sound="default",
                    category="SNAKE_CLASSIC_NOTIFICATION"
                )
            )
        )
        
        # Create the message
        message = messaging.Message(
            notification=notification,
            data=data,
            android=android_config,
            apns=ios_config,
            token=token,
            topic=topic,
            condition=condition
        )
        
        return message
    
    async def send_to_token(self, request: IndividualNotificationRequest) -> NotificationResponse:
        """Send notification to a specific FCM token."""
        try:
            if not self._initialized:
                raise Exception("Firebase service not initialized")
            
            message = self._create_message(request, token=request.fcm_token)
            
            # Send message
            message_id = messaging.send(message)
            
            logger.info(f"Notification sent successfully to token {request.fcm_token[:10]}...*, message ID: {message_id}")
            
            return NotificationResponse(
                success=True,
                message="Notification sent successfully",
                message_id=message_id,
                success_count=1,
                failure_count=0
            )
            
        except messaging.UnregisteredError:
            logger.warning(f"FCM token is no longer valid: {request.fcm_token[:10]}...")
            return NotificationResponse(
                success=False,
                message="FCM token is no longer valid",
                success_count=0,
                failure_count=1,
                errors=["Invalid or unregistered FCM token"]
            )
            
        except Exception as e:
            logger.error(f"Failed to send notification to token: {e}")
            return NotificationResponse(
                success=False,
                message=f"Failed to send notification: {str(e)}",
                success_count=0,
                failure_count=1,
                errors=[str(e)]
            )
    
    async def send_to_topic(self, request: TopicNotificationRequest) -> NotificationResponse:
        """Send notification to a topic."""
        try:
            if not self._initialized:
                raise Exception("Firebase service not initialized")
            
            message = self._create_message(
                request, 
                topic=request.topic,
                condition=request.condition
            )
            
            # Send message
            message_id = messaging.send(message)
            
            logger.info(f"Notification sent successfully to topic '{request.topic}', message ID: {message_id}")
            
            return NotificationResponse(
                success=True,
                message=f"Notification sent to topic '{request.topic}'",
                message_id=message_id
            )
            
        except Exception as e:
            logger.error(f"Failed to send notification to topic '{request.topic}': {e}")
            return NotificationResponse(
                success=False,
                message=f"Failed to send notification to topic: {str(e)}",
                errors=[str(e)]
            )
    
    async def send_multicast(
        self, 
        notification_data: NotificationRequest, 
        tokens: List[str]
    ) -> NotificationResponse:
        """Send notification to multiple FCM tokens."""
        try:
            if not self._initialized:
                raise Exception("Firebase service not initialized")
            
            if not tokens:
                return NotificationResponse(
                    success=False,
                    message="No tokens provided",
                    success_count=0,
                    failure_count=0,
                    errors=["No tokens provided"]
                )
            
            # Create multicast message
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=notification_data.title,
                    body=notification_data.body,
                    image=notification_data.image_url
                ),
                data={k: str(v) for k, v in (notification_data.data or {}).items()},
                tokens=tokens,
                android=messaging.AndroidConfig(
                    priority="high" if notification_data.priority == NotificationPriority.HIGH else "normal"
                )
            )
            
            # Send multicast message
            response = messaging.send_multicast(message)
            
            logger.info(f"Multicast sent: {response.success_count} successful, {response.failure_count} failed")
            
            # Collect error messages
            errors = []
            for idx, result in enumerate(response.responses):
                if not result.success:
                    error_msg = f"Token {idx}: {result.exception}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
            
            return NotificationResponse(
                success=response.failure_count == 0,
                message=f"Sent to {response.success_count}/{len(tokens)} recipients",
                success_count=response.success_count,
                failure_count=response.failure_count,
                errors=errors if errors else None
            )
            
        except Exception as e:
            logger.error(f"Failed to send multicast notification: {e}")
            return NotificationResponse(
                success=False,
                message=f"Failed to send multicast notification: {str(e)}",
                success_count=0,
                failure_count=len(tokens),
                errors=[str(e)]
            )
    
    async def subscribe_to_topic(self, tokens: Union[str, List[str]], topic: str) -> Dict[str, Any]:
        """Subscribe FCM tokens to a topic."""
        try:
            if not self._initialized:
                raise Exception("Firebase service not initialized")
            
            token_list = [tokens] if isinstance(tokens, str) else tokens
            
            response = messaging.subscribe_to_topic(token_list, topic)
            
            logger.info(f"Subscribed {len(token_list)} tokens to topic '{topic}'. Success: {response.success_count}, Failed: {response.failure_count}")
            
            return {
                "success": response.failure_count == 0,
                "message": f"Subscribed {response.success_count}/{len(token_list)} tokens to topic '{topic}'",
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "errors": [str(error.reason) for error in response.errors] if response.errors else None
            }
            
        except Exception as e:
            logger.error(f"Failed to subscribe tokens to topic '{topic}': {e}")
            return {
                "success": False,
                "message": f"Failed to subscribe to topic: {str(e)}",
                "errors": [str(e)]
            }
    
    async def unsubscribe_from_topic(self, tokens: Union[str, List[str]], topic: str) -> Dict[str, Any]:
        """Unsubscribe FCM tokens from a topic."""
        try:
            if not self._initialized:
                raise Exception("Firebase service not initialized")
            
            token_list = [tokens] if isinstance(tokens, str) else tokens
            
            response = messaging.unsubscribe_from_topic(token_list, topic)
            
            logger.info(f"Unsubscribed {len(token_list)} tokens from topic '{topic}'. Success: {response.success_count}, Failed: {response.failure_count}")
            
            return {
                "success": response.failure_count == 0,
                "message": f"Unsubscribed {response.success_count}/{len(token_list)} tokens from topic '{topic}'",
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "errors": [str(error.reason) for error in response.errors] if response.errors else None
            }
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe tokens from topic '{topic}': {e}")
            return {
                "success": False,
                "message": f"Failed to unsubscribe from topic: {str(e)}",
                "errors": [str(e)]
            }
    
    async def validate_token(self, token: str) -> bool:
        """Validate if an FCM token is still valid."""
        try:
            if not self._initialized:
                raise Exception("Firebase service not initialized")
            
            # Create a simple test message without sending
            test_message = messaging.Message(
                data={"test": "true"},
                token=token
            )
            
            # This will validate the token format and existence
            # We'll send a dry run to check validity
            messaging.send(test_message, dry_run=True)
            return True
            
        except messaging.UnregisteredError:
            return False
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return False


# Global Firebase service instance
firebase_service = FirebaseService()