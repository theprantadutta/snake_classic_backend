"""
Purchase schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class PurchaseReceipt(BaseModel):
    """Purchase receipt data from app stores"""
    platform: str = Field(..., description="Platform (android/ios)")
    receipt_data: str = Field(..., description="Base64 encoded receipt")
    product_id: str = Field(..., description="Product identifier")
    transaction_id: str = Field(..., description="Transaction identifier")
    purchase_token: Optional[str] = Field(None, description="Purchase token (Android)")
    purchase_time: datetime = Field(..., description="Purchase timestamp")


class PurchaseVerifyRequest(BaseModel):
    """Request to verify a purchase"""
    receipt: PurchaseReceipt
    device_info: Dict[str, Any] = Field(default_factory=dict)


class PurchaseVerifyResponse(BaseModel):
    """Response from purchase verification"""
    success: bool
    valid: bool
    product_id: str
    transaction_id: str
    content_unlocked: List[str] = []
    is_subscription: bool = False
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None


class PurchaseResponse(BaseModel):
    """Purchase record response"""
    id: UUID
    product_id: str
    transaction_id: str
    platform: str
    is_verified: bool
    is_subscription: bool
    expires_at: Optional[datetime] = None
    content_unlocked: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class RestorePurchasesRequest(BaseModel):
    """Request to restore purchases"""
    platform: str
    receipts: List[PurchaseReceipt]


class RestorePurchasesResponse(BaseModel):
    """Response from restoring purchases"""
    restored_count: int
    failed_count: int
    restored_products: List[Dict[str, Any]] = []
    failed_restorations: List[Dict[str, Any]] = []


class PremiumContentResponse(BaseModel):
    """User's premium content"""
    user_id: UUID
    premium_tier: str = "free"
    subscription_active: bool = False
    subscription_expires_at: Optional[datetime] = None
    battle_pass_active: bool = False
    battle_pass_tier: int = 0
    owned_themes: List[str] = []
    owned_powerups: List[str] = []
    owned_cosmetics: List[str] = []
    coins: int = 0

    class Config:
        from_attributes = True
