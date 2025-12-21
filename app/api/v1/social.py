"""
Social/Friends API endpoints
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.social import (
    FriendRequestCreate,
    FriendRequestResponse,
    FriendListResponse,
    PendingRequestsResponse,
    FriendActionResponse,
)
from app.services.social_service import social_service

router = APIRouter(prefix="/social", tags=["social"])


@router.get("/friends", response_model=FriendListResponse)
async def get_friends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's friends list"""
    return social_service.get_friends(db, current_user.id)


@router.get("/requests", response_model=PendingRequestsResponse)
async def get_pending_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending friend requests (incoming and outgoing)"""
    return social_service.get_pending_requests(db, current_user.id)


@router.post("/friends/request", response_model=FriendActionResponse)
async def send_friend_request(
    request: FriendRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a friend request to another user"""
    try:
        friendship, message = social_service.send_friend_request(
            db,
            current_user.id,
            friend_username=request.friend_username,
            friend_user_id=request.friend_user_id
        )
        return FriendActionResponse(
            success=True,
            message=message,
            friendship_id=friendship.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/friends/accept/{request_id}", response_model=FriendActionResponse)
async def accept_friend_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept a friend request"""
    try:
        friendship = social_service.accept_friend_request(db, current_user.id, request_id)
        return FriendActionResponse(
            success=True,
            message="Friend request accepted",
            friendship_id=friendship.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/friends/reject/{request_id}", response_model=FriendActionResponse)
async def reject_friend_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a friend request"""
    try:
        social_service.reject_friend_request(db, current_user.id, request_id)
        return FriendActionResponse(
            success=True,
            message="Friend request rejected"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/friends/cancel/{request_id}", response_model=FriendActionResponse)
async def cancel_friend_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a sent friend request"""
    try:
        social_service.cancel_friend_request(db, current_user.id, request_id)
        return FriendActionResponse(
            success=True,
            message="Friend request cancelled"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/friends/{friend_id}", response_model=FriendActionResponse)
async def remove_friend(
    friend_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a friend"""
    try:
        social_service.remove_friend(db, current_user.id, friend_id)
        return FriendActionResponse(
            success=True,
            message="Friend removed"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/friends/check/{user_id}")
async def check_friendship(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if you are friends with another user"""
    is_friend = social_service.are_friends(db, current_user.id, user_id)
    return {"is_friend": is_friend, "user_id": user_id}


@router.get("/friends/count")
async def get_friend_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get friend count for current user"""
    count = social_service.get_friend_count(db, current_user.id)
    return {"count": count}
