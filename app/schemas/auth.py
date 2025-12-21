"""Authentication schemas"""
from pydantic import BaseModel, Field
from typing import Optional


class FirebaseAuthRequest(BaseModel):
    """Request to authenticate with Firebase token"""
    firebase_token: str = Field(..., description="Firebase ID token from client")


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user_id: str


class TokenData(BaseModel):
    """Token payload data"""
    user_id: Optional[str] = None
