"""
Timezone-aware datetime utilities for consistent timestamp handling.

This module provides centralized functions for creating and formatting
UTC timestamps to ensure consistency across the entire application.
All timestamps are stored and transmitted in UTC with explicit timezone info.
"""
from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """
    Return current UTC time with timezone info.

    Use this instead of datetime.utcnow() which returns naive datetimes.

    Returns:
        datetime: Current UTC time with tzinfo set to timezone.utc
    """
    return datetime.now(timezone.utc)


def to_utc_isoformat(dt: Optional[datetime]) -> Optional[str]:
    """
    Convert datetime to ISO 8601 string with 'Z' suffix indicating UTC.

    Args:
        dt: Datetime to convert (can be naive or timezone-aware)

    Returns:
        ISO 8601 formatted string with 'Z' suffix, or None if dt is None
        Example: "2024-11-29T10:30:45.123Z"
    """
    if dt is None:
        return None

    # If naive datetime, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC if it has a different timezone
        dt = dt.astimezone(timezone.utc)

    # Format with milliseconds and Z suffix
    return dt.strftime('%Y-%m-%dT%H:%M:%S.') + f'{dt.microsecond // 1000:03d}Z'


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure datetime has UTC timezone info.

    Converts naive datetimes to UTC-aware datetimes by assuming they are already in UTC.
    Converts timezone-aware datetimes to UTC.

    Args:
        dt: Datetime to convert

    Returns:
        UTC timezone-aware datetime, or None if dt is None
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)
