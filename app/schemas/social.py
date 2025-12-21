"""
Social and friends schemas
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel


class FriendRequestCreate(BaseModel):
    """Create friend request"""
    friend_username: Optional[str] = None
    friend_user_id: Optional[UUID] = None


class FriendRequestResponse(BaseModel):
    """Friend request response"""
    id: UUID
    user_id: UUID
    friend_id: UUID
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FriendInfo(BaseModel):
    """Friend basic info"""
    id: UUID
    username: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    status: Optional[str] = None
    high_score: int = 0
    last_seen: Optional[datetime] = None


class FriendWithRequestInfo(BaseModel):
    """Friend with request metadata"""
    friend: FriendInfo
    friendship_id: UUID
    friendship_status: str
    since: datetime


class FriendRequestWithUser(BaseModel):
    """Friend request with user info"""
    request_id: UUID
    from_user: FriendInfo
    status: str
    created_at: datetime


class FriendListResponse(BaseModel):
    """Response with list of friends"""
    friends: List[FriendWithRequestInfo]
    total_count: int


class PendingRequestsResponse(BaseModel):
    """Response with pending friend requests"""
    incoming: List[FriendRequestWithUser]
    outgoing: List[FriendRequestWithUser]
    incoming_count: int
    outgoing_count: int


class FriendActionResponse(BaseModel):
    """Response after friend action (accept/reject/remove)"""
    success: bool
    message: str
    friendship_id: Optional[UUID] = None
