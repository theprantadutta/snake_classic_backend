"""
Social service for managing friends and friend requests
"""
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.social import Friendship
from app.models.user import User
from app.schemas.social import (
    FriendInfo,
    FriendWithRequestInfo,
    FriendListResponse,
    FriendRequestWithUser,
    PendingRequestsResponse,
)
from app.utils.time_utils import utc_now


class SocialService:
    """Service for social/friend operations"""

    def send_friend_request(
        self,
        db: Session,
        user_id: UUID,
        friend_username: Optional[str] = None,
        friend_user_id: Optional[UUID] = None
    ) -> Tuple[Friendship, str]:
        """
        Send a friend request.
        Returns: (friendship, status_message)
        """
        # Find target user
        if friend_user_id:
            friend = db.query(User).filter(User.id == friend_user_id).first()
        elif friend_username:
            friend = db.query(User).filter(User.username == friend_username).first()
        else:
            raise ValueError("Must provide friend_username or friend_user_id")

        if not friend:
            raise ValueError("User not found")

        if friend.id == user_id:
            raise ValueError("Cannot send friend request to yourself")

        # Check if friendship already exists
        existing = db.query(Friendship).filter(
            or_(
                and_(Friendship.user_id == user_id, Friendship.friend_id == friend.id),
                and_(Friendship.user_id == friend.id, Friendship.friend_id == user_id)
            )
        ).first()

        if existing:
            if existing.status == "accepted":
                raise ValueError("Already friends")
            elif existing.status == "pending":
                if existing.user_id == user_id:
                    raise ValueError("Friend request already sent")
                else:
                    # They already sent us a request - accept it
                    existing.status = "accepted"
                    existing.updated_at = utc_now()
                    db.commit()
                    return existing, "Friend request accepted (they already sent you one)"
            elif existing.status == "blocked":
                raise ValueError("Unable to send friend request")

        # Create new friend request
        friendship = Friendship(
            user_id=user_id,
            friend_id=friend.id,
            status="pending"
        )
        db.add(friendship)
        db.commit()
        db.refresh(friendship)

        return friendship, "Friend request sent"

    def accept_friend_request(
        self,
        db: Session,
        user_id: UUID,
        request_id: UUID
    ) -> Friendship:
        """Accept a friend request"""
        friendship = db.query(Friendship).filter(
            Friendship.id == request_id,
            Friendship.friend_id == user_id,  # We are the recipient
            Friendship.status == "pending"
        ).first()

        if not friendship:
            raise ValueError("Friend request not found")

        friendship.status = "accepted"
        friendship.updated_at = utc_now()
        db.commit()
        db.refresh(friendship)

        return friendship

    def reject_friend_request(
        self,
        db: Session,
        user_id: UUID,
        request_id: UUID
    ) -> bool:
        """Reject a friend request"""
        friendship = db.query(Friendship).filter(
            Friendship.id == request_id,
            Friendship.friend_id == user_id,
            Friendship.status == "pending"
        ).first()

        if not friendship:
            raise ValueError("Friend request not found")

        db.delete(friendship)
        db.commit()
        return True

    def cancel_friend_request(
        self,
        db: Session,
        user_id: UUID,
        request_id: UUID
    ) -> bool:
        """Cancel a sent friend request"""
        friendship = db.query(Friendship).filter(
            Friendship.id == request_id,
            Friendship.user_id == user_id,  # We are the sender
            Friendship.status == "pending"
        ).first()

        if not friendship:
            raise ValueError("Friend request not found")

        db.delete(friendship)
        db.commit()
        return True

    def remove_friend(
        self,
        db: Session,
        user_id: UUID,
        friend_id: UUID
    ) -> bool:
        """Remove a friend"""
        friendship = db.query(Friendship).filter(
            or_(
                and_(Friendship.user_id == user_id, Friendship.friend_id == friend_id),
                and_(Friendship.user_id == friend_id, Friendship.friend_id == user_id)
            ),
            Friendship.status == "accepted"
        ).first()

        if not friendship:
            raise ValueError("Friendship not found")

        db.delete(friendship)
        db.commit()
        return True

    def get_friends(self, db: Session, user_id: UUID) -> FriendListResponse:
        """Get list of friends"""
        # Get all accepted friendships
        friendships = db.query(Friendship).filter(
            or_(
                Friendship.user_id == user_id,
                Friendship.friend_id == user_id
            ),
            Friendship.status == "accepted"
        ).all()

        friends = []
        for fs in friendships:
            # Get the friend (the other person)
            friend_id = fs.friend_id if fs.user_id == user_id else fs.user_id
            friend_user = db.query(User).filter(User.id == friend_id).first()

            if friend_user:
                friends.append(FriendWithRequestInfo(
                    friend=FriendInfo(
                        id=friend_user.id,
                        username=friend_user.username,
                        display_name=friend_user.display_name,
                        photo_url=friend_user.photo_url,
                        status=friend_user.status,
                        high_score=friend_user.high_score or 0,
                        last_seen=friend_user.last_seen
                    ),
                    friendship_id=fs.id,
                    friendship_status=fs.status,
                    since=fs.updated_at or fs.created_at
                ))

        return FriendListResponse(
            friends=friends,
            total_count=len(friends)
        )

    def get_pending_requests(
        self,
        db: Session,
        user_id: UUID
    ) -> PendingRequestsResponse:
        """Get pending friend requests (both incoming and outgoing)"""
        # Incoming requests (we are friend_id)
        incoming = db.query(Friendship).filter(
            Friendship.friend_id == user_id,
            Friendship.status == "pending"
        ).all()

        incoming_requests = []
        for fs in incoming:
            sender = db.query(User).filter(User.id == fs.user_id).first()
            if sender:
                incoming_requests.append(FriendRequestWithUser(
                    request_id=fs.id,
                    from_user=FriendInfo(
                        id=sender.id,
                        username=sender.username,
                        display_name=sender.display_name,
                        photo_url=sender.photo_url,
                        status=sender.status,
                        high_score=sender.high_score or 0,
                        last_seen=sender.last_seen
                    ),
                    status=fs.status,
                    created_at=fs.created_at
                ))

        # Outgoing requests (we are user_id)
        outgoing = db.query(Friendship).filter(
            Friendship.user_id == user_id,
            Friendship.status == "pending"
        ).all()

        outgoing_requests = []
        for fs in outgoing:
            recipient = db.query(User).filter(User.id == fs.friend_id).first()
            if recipient:
                outgoing_requests.append(FriendRequestWithUser(
                    request_id=fs.id,
                    from_user=FriendInfo(
                        id=recipient.id,
                        username=recipient.username,
                        display_name=recipient.display_name,
                        photo_url=recipient.photo_url,
                        status=recipient.status,
                        high_score=recipient.high_score or 0,
                        last_seen=recipient.last_seen
                    ),
                    status=fs.status,
                    created_at=fs.created_at
                ))

        return PendingRequestsResponse(
            incoming=incoming_requests,
            outgoing=outgoing_requests,
            incoming_count=len(incoming_requests),
            outgoing_count=len(outgoing_requests)
        )

    def are_friends(self, db: Session, user_id: UUID, other_user_id: UUID) -> bool:
        """Check if two users are friends"""
        friendship = db.query(Friendship).filter(
            or_(
                and_(Friendship.user_id == user_id, Friendship.friend_id == other_user_id),
                and_(Friendship.user_id == other_user_id, Friendship.friend_id == user_id)
            ),
            Friendship.status == "accepted"
        ).first()
        return friendship is not None

    def get_friend_count(self, db: Session, user_id: UUID) -> int:
        """Get count of friends"""
        count = db.query(Friendship).filter(
            or_(
                Friendship.user_id == user_id,
                Friendship.friend_id == user_id
            ),
            Friendship.status == "accepted"
        ).count()
        return count


social_service = SocialService()
