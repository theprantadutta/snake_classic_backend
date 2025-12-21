"""
Authentication Service - Firebase verification and JWT management
"""
import firebase_admin
from firebase_admin import auth, credentials
from typing import Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User, UserPreferences, UserPremiumContent
from app.utils.time_utils import utc_now
import logging
import os

logger = logging.getLogger(__name__)


def _ensure_firebase_initialized():
    """
    Ensure Firebase Admin SDK is initialized before use
    Raises RuntimeError if not initialized
    """
    if not firebase_admin._apps:
        if os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
            try:
                cred = credentials.Certificate(settings.GOOGLE_APPLICATION_CREDENTIALS)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
                raise RuntimeError(
                    f"Firebase Admin SDK initialization failed: {e}\n"
                    f"Check that {settings.GOOGLE_APPLICATION_CREDENTIALS} is valid."
                )
        else:
            raise RuntimeError(
                f"Firebase Admin SDK not initialized and credentials file not found: {settings.GOOGLE_APPLICATION_CREDENTIALS}\n"
                f"Please download credentials from Firebase Console."
            )


def verify_firebase_token(id_token: str) -> Optional[Dict]:
    """
    Verify Firebase ID token and return decoded token

    Args:
        id_token: Firebase ID token from client

    Returns:
        Decoded token dict or None if invalid

    Raises:
        ValueError: If token is invalid
        RuntimeError: If Firebase Admin SDK not initialized
    """
    _ensure_firebase_initialized()

    try:
        decoded_token = auth.verify_id_token(id_token)
        logger.info(f"Firebase token verified for UID: {decoded_token['uid']}")
        return decoded_token
    except auth.InvalidIdTokenError as e:
        logger.error(f"Invalid Firebase ID token: {e}")
        raise ValueError(f"Invalid Firebase token: {str(e)}")
    except auth.ExpiredIdTokenError as e:
        logger.error(f"Expired Firebase ID token: {e}")
        raise ValueError(f"Firebase token expired: {str(e)}")
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {e}")
        raise ValueError(f"Token verification failed: {str(e)}")


def get_user_info_from_token(decoded_token: Dict) -> Dict:
    """
    Extract user information from decoded Firebase token

    Args:
        decoded_token: Decoded Firebase ID token

    Returns:
        Dictionary with user information
    """
    provider_data = decoded_token.get('firebase', {}).get('sign_in_provider', 'unknown')

    user_info = {
        'firebase_uid': decoded_token['uid'],
        'email': decoded_token.get('email'),
        'email_verified': decoded_token.get('email_verified', False),
        'display_name': decoded_token.get('name'),
        'photo_url': decoded_token.get('picture'),
        'auth_provider': 'google' if provider_data == 'google.com' else 'anonymous' if provider_data == 'anonymous' else 'firebase',
        'is_anonymous': provider_data == 'anonymous',
    }

    if provider_data == 'google.com':
        user_info['google_id'] = decoded_token.get('sub')

    logger.info(f"Extracted user info for: {user_info.get('email', 'anonymous')}")
    return user_info


class AuthService:
    """Service for authentication operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        """Get user by Firebase UID"""
        return self.db.query(User).filter(User.firebase_uid == firebase_uid).first()

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            return self.db.query(User).filter(User.id == user_uuid).first()
        except (ValueError, TypeError):
            return None

    def create_user_from_firebase(self, user_info: Dict) -> User:
        """
        Create a new user from Firebase authentication info

        Args:
            user_info: Dictionary with user information from Firebase

        Returns:
            Newly created User object
        """
        user = User(
            email=user_info.get('email'),
            firebase_uid=user_info['firebase_uid'],
            auth_provider=user_info.get('auth_provider', 'google'),
            is_anonymous=user_info.get('is_anonymous', False),
            display_name=user_info.get('display_name'),
            photo_url=user_info.get('photo_url'),
            is_active=True,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        logger.info(f"Created new user with ID: {user.id}")

        # Create user preferences
        preferences = UserPreferences(user_id=user.id)
        self.db.add(preferences)

        # Create user premium content record
        premium_content = UserPremiumContent(user_id=user.id)
        self.db.add(premium_content)

        self.db.commit()

        logger.info(f"Created preferences and premium content for user: {user.id}")

        return user

    def update_user_last_seen(self, user: User) -> User:
        """Update user's last seen timestamp"""
        user.last_seen = utc_now()
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_access_token_for_user(self, user: User) -> str:
        """Create JWT access token for user"""
        return create_access_token(data={"sub": str(user.id)})
