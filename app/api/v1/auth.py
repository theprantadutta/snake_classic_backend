"""
Authentication endpoints - Firebase token verification and JWT management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import FirebaseAuthRequest, Token
from app.schemas.user import UserResponse
from app.services.auth_service import (
    AuthService,
    verify_firebase_token,
    get_user_info_from_token
)
from app.core.dependencies import get_current_user
from app.models.user import User
from app.utils.time_utils import utc_now
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/firebase", response_model=Token, status_code=status.HTTP_200_OK)
async def authenticate_with_firebase(
    request: FirebaseAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user with Firebase ID token

    This endpoint:
    1. Verifies the Firebase ID token
    2. Extracts user information
    3. Creates user if doesn't exist or logs in existing user
    4. Returns backend JWT token

    - **firebase_token**: Firebase ID token from client (from Google Sign-In or Anonymous auth)
    """
    try:
        logger.info("Starting Firebase authentication...")

        # Verify Firebase token
        decoded_token = verify_firebase_token(request.firebase_token)
        logger.info(f"Token verified for UID: {decoded_token.get('uid')}")

        # Extract user info
        user_info = get_user_info_from_token(decoded_token)
        logger.info(f"User info extracted: {user_info.get('email', 'anonymous')}")

        auth_service = AuthService(db)

        # Check if user exists by Firebase UID
        user = auth_service.get_user_by_firebase_uid(user_info['firebase_uid'])

        if user:
            # Existing user - update last seen
            logger.info(f"Found existing user: {user.id}")
            auth_service.update_user_last_seen(user)
            is_new_user = False
        else:
            # Create new user
            logger.info("Creating new user...")
            user = auth_service.create_user_from_firebase(user_info)
            is_new_user = True
            logger.info(f"Created new user: {user.id}")

        # Create backend JWT token
        access_token = auth_service.create_access_token_for_user(user)
        logger.info(f"Authentication successful for user: {user.id}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": str(user.id)
        }

    except ValueError as e:
        logger.error(f"Firebase token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase token: {str(e)}"
        )
    except RuntimeError as e:
        logger.error(f"Firebase SDK error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Firebase initialization error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {type(e).__name__}: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information

    Returns the user profile for the authenticated user.
    Requires Bearer token in Authorization header.
    """
    return current_user


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout user

    Currently, JWT tokens are stateless so this is mostly for client-side cleanup.
    In the future, we could implement token blacklisting here.
    """
    logger.info(f"User logged out: {current_user.id}")

    return {
        "success": True,
        "message": "Logged out successfully"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Refresh JWT token

    Returns a new JWT token for the authenticated user.
    Useful for extending session without re-authenticating with Firebase.
    """
    auth_service = AuthService(db)
    access_token = auth_service.create_access_token_for_user(current_user)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(current_user.id)
    }
