"""User schemas for request/response validation"""
from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    """Base user schema"""
    email: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user (internal use)"""
    firebase_uid: str
    auth_provider: str = "google"
    is_anonymous: bool = False


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    username: Optional[str] = Field(None, min_length=3, max_length=20)
    display_name: Optional[str] = Field(None, max_length=255)
    photo_url: Optional[str] = None
    status_message: Optional[str] = Field(None, max_length=255)
    is_public: Optional[bool] = None


class UserPreferencesUpdate(BaseModel):
    """Schema for updating user preferences"""
    theme: Optional[str] = None
    sound_enabled: Optional[bool] = None
    music_enabled: Optional[bool] = None
    vibration_enabled: Optional[bool] = None
    notifications_enabled: Optional[bool] = None


class UserPreferencesResponse(BaseModel):
    """Schema for user preferences response"""
    theme: str
    sound_enabled: bool
    music_enabled: bool
    vibration_enabled: bool
    notifications_enabled: bool

    class Config:
        from_attributes = True


class UserPremiumContentResponse(BaseModel):
    """Schema for user premium content response"""
    premium_tier: str
    subscription_active: bool
    subscription_expires_at: Optional[datetime] = None
    battle_pass_active: bool
    battle_pass_expires_at: Optional[datetime] = None
    battle_pass_tier: int
    owned_themes: List[str]
    owned_powerups: List[str]
    owned_cosmetics: List[str]

    @field_serializer('subscription_expires_at', 'battle_pass_expires_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        return value.isoformat()

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Schema for user response"""
    id: UUID
    email: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    auth_provider: str
    is_anonymous: bool
    status: str
    status_message: Optional[str] = None
    is_public: bool
    high_score: int
    total_games_played: int
    total_score: int
    level: int
    coins: int
    joined_date: datetime
    last_seen: datetime
    is_premium: bool

    @field_serializer('joined_date', 'last_seen')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        return value.isoformat()

    class Config:
        from_attributes = True


class UserProfileResponse(UserResponse):
    """Extended user profile with preferences and premium content"""
    preferences: Optional[UserPreferencesResponse] = None
    premium_content: Optional[UserPremiumContentResponse] = None


class UsernameCheckRequest(BaseModel):
    """Request to check username availability"""
    username: str = Field(..., min_length=3, max_length=20)


class UsernameCheckResponse(BaseModel):
    """Response for username availability check"""
    username: str
    available: bool
    message: str


class UserSearchResponse(BaseModel):
    """Schema for user search result"""
    id: UUID
    username: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    level: int
    high_score: int
    is_public: bool

    class Config:
        from_attributes = True
