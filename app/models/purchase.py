"""
In-app purchase models
"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.time_utils import utc_now


class Purchase(Base):
    """Individual purchase transaction"""
    __tablename__ = "purchases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Purchase details
    product_id = Column(String(100), nullable=False, index=True)
    transaction_id = Column(String(255), unique=True, nullable=False, index=True)
    platform = Column(String(20), nullable=False)  # 'android', 'ios'

    # Receipt data for verification
    receipt_data = Column(Text, nullable=True)

    # Verification status
    is_verified = Column(Boolean, default=False)
    verification_error = Column(Text, nullable=True)

    # Subscription details (for subscription purchases)
    is_subscription = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=True)
    auto_renewing = Column(Boolean, default=False)

    # Content unlocked by this purchase
    content_unlocked = Column(JSONB, default=list)

    # Timestamps
    purchase_timestamp = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    user = relationship("User")


class NotificationHistory(Base):
    """History of sent notifications"""
    __tablename__ = "notification_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    notification_id = Column(String(100), nullable=True)

    # Notification content
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    type = Column(String(50), default="general")  # 'tournament', 'social', 'achievement', etc.
    priority = Column(String(20), default="normal")  # 'low', 'normal', 'high'

    # Delivery stats
    recipient_type = Column(String(50), default="token")  # 'token', 'topic', 'multicast'
    recipients_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)

    # Additional data
    extra_data = Column(JSONB, default=dict)

    # Timestamps
    sent_at = Column(DateTime, default=utc_now, index=True)


class ScheduledJob(Base):
    """Stored scheduled job for persistence"""
    __tablename__ = "scheduled_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    job_name = Column(String(255), nullable=False)

    # Trigger configuration
    trigger_type = Column(String(50), default="date")  # 'cron', 'date', 'interval'
    trigger_config = Column(JSONB, default=dict)

    # Job configuration
    job_type = Column(String(50), default="notification")
    payload = Column(JSONB, default=dict)

    # Status
    next_run_time = Column(DateTime, nullable=True, index=True)
    status = Column(String(50), default="pending")  # 'pending', 'running', 'completed', 'failed'

    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
