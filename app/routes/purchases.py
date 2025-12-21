"""
Purchase verification endpoints for Snake Classic game.
Handles in-app purchase verification and premium content management.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
import json
import hmac
import hashlib
import base64

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/purchases",
    tags=["purchases"],
    responses={
        500: {"description": "Internal server error"},
        400: {"description": "Bad request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
    },
)

# Pydantic models for request/response validation

class PurchaseReceipt(BaseModel):
    """Purchase receipt data from app stores."""
    platform: str = Field(..., description="Platform (android/ios)")
    receipt_data: str = Field(..., description="Base64 encoded receipt")
    product_id: str = Field(..., description="Product identifier")
    transaction_id: str = Field(..., description="Transaction identifier")
    purchase_token: Optional[str] = Field(None, description="Purchase token (Android)")
    user_id: str = Field(..., description="User ID")
    purchase_time: datetime = Field(..., description="Purchase timestamp")

class SubscriptionInfo(BaseModel):
    """Subscription information."""
    product_id: str
    is_active: bool
    expires_at: Optional[datetime] = None
    auto_renewing: bool = False
    original_transaction_id: str
    latest_receipt: Optional[str] = None

class PurchaseVerificationRequest(BaseModel):
    """Request to verify a purchase."""
    receipt: PurchaseReceipt
    user_id: str
    device_info: Dict[str, Any] = Field(default_factory=dict)

class PurchaseVerificationResponse(BaseModel):
    """Response from purchase verification."""
    success: bool
    valid: bool
    product_id: str
    user_id: str
    transaction_id: str
    premium_content_unlocked: List[str] = Field(default_factory=list)
    subscription_info: Optional[SubscriptionInfo] = None
    error_message: Optional[str] = None
    verification_timestamp: datetime = Field(default_factory=datetime.now)

class PremiumContentRequest(BaseModel):
    """Request to get user's premium content."""
    user_id: str
    include_expired: bool = False

class PremiumContentResponse(BaseModel):
    """User's premium content information."""
    user_id: str
    premium_tier: str  # free, pro
    subscription_active: bool
    subscription_expires_at: Optional[datetime] = None
    owned_themes: List[str] = Field(default_factory=list)
    owned_powerups: List[str] = Field(default_factory=list)
    owned_cosmetics: List[str] = Field(default_factory=list)
    battle_pass_active: bool = False
    battle_pass_expires_at: Optional[datetime] = None
    battle_pass_tier: int = 0
    tournament_entries: Dict[str, int] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)

class RestorePurchasesRequest(BaseModel):
    """Request to restore user purchases."""
    user_id: str
    platform: str
    receipts: List[PurchaseReceipt]

# In-memory storage for demo purposes
# In production, this should be a proper database
user_purchases: Dict[str, Dict] = {}
verified_transactions: Dict[str, Dict] = {}

@router.post("/verify", response_model=PurchaseVerificationResponse)
async def verify_purchase(
    request: PurchaseVerificationRequest,
    background_tasks: BackgroundTasks
) -> PurchaseVerificationResponse:
    """
    Verify a purchase receipt with the app store.
    
    This endpoint validates purchase receipts from Google Play Store or Apple App Store
    and unlocks premium content for the user.
    """
    try:
        logger.info(f"Verifying purchase for user {request.user_id}, product {request.receipt.product_id}")
        
        # Check if transaction was already verified
        if request.receipt.transaction_id in verified_transactions:
            existing = verified_transactions[request.receipt.transaction_id]
            logger.warning(f"Transaction {request.receipt.transaction_id} already verified")
            return PurchaseVerificationResponse(
                success=True,
                valid=True,
                product_id=existing["product_id"],
                user_id=existing["user_id"],
                transaction_id=request.receipt.transaction_id,
                premium_content_unlocked=existing.get("content_unlocked", []),
                error_message="Transaction already verified"
            )
        
        # Verify with app store
        verification_result = await _verify_with_app_store(request.receipt)
        
        if not verification_result["valid"]:
            logger.error(f"Purchase verification failed for {request.receipt.product_id}")
            return PurchaseVerificationResponse(
                success=True,
                valid=False,
                product_id=request.receipt.product_id,
                user_id=request.user_id,
                transaction_id=request.receipt.transaction_id,
                error_message=verification_result.get("error", "Purchase verification failed")
            )
        
        # Determine what content to unlock
        content_unlocked = _determine_premium_content(request.receipt.product_id)
        
        # Update user's premium status
        await _update_user_premium_status(
            request.user_id,
            request.receipt.product_id,
            request.receipt.transaction_id,
            content_unlocked
        )
        
        # Record verified transaction
        verified_transactions[request.receipt.transaction_id] = {
            "product_id": request.receipt.product_id,
            "user_id": request.user_id,
            "content_unlocked": content_unlocked,
            "verified_at": datetime.now().isoformat(),
            "platform": request.receipt.platform
        }
        
        # Handle subscription products
        subscription_info = None
        if _is_subscription_product(request.receipt.product_id):
            subscription_info = await _handle_subscription(request.receipt)
        
        # Schedule background tasks
        background_tasks.add_task(
            _log_purchase_analytics,
            request.user_id,
            request.receipt.product_id,
            verification_result
        )
        
        logger.info(f"Purchase verified successfully for user {request.user_id}")
        
        return PurchaseVerificationResponse(
            success=True,
            valid=True,
            product_id=request.receipt.product_id,
            user_id=request.user_id,
            transaction_id=request.receipt.transaction_id,
            premium_content_unlocked=content_unlocked,
            subscription_info=subscription_info
        )
        
    except Exception as e:
        logger.error(f"Error verifying purchase: {e}", exc_info=True)
        return PurchaseVerificationResponse(
            success=False,
            valid=False,
            product_id=request.receipt.product_id,
            user_id=request.user_id,
            transaction_id=request.receipt.transaction_id,
            error_message=f"Verification error: {str(e)}"
        )

@router.post("/restore", response_model=Dict[str, Any])
async def restore_purchases(request: RestorePurchasesRequest) -> Dict[str, Any]:
    """
    Restore user's previous purchases.
    
    This endpoint processes multiple receipts to restore all of a user's
    premium content and subscriptions.
    """
    try:
        logger.info(f"Restoring purchases for user {request.user_id}")
        
        restored_products = []
        failed_restorations = []
        
        for receipt in request.receipts:
            try:
                # Verify each receipt
                verification_result = await _verify_with_app_store(receipt)
                
                if verification_result["valid"]:
                    # Determine content to unlock
                    content_unlocked = _determine_premium_content(receipt.product_id)
                    
                    # Update user's premium status
                    await _update_user_premium_status(
                        request.user_id,
                        receipt.product_id,
                        receipt.transaction_id,
                        content_unlocked
                    )
                    
                    restored_products.append({
                        "product_id": receipt.product_id,
                        "transaction_id": receipt.transaction_id,
                        "content_unlocked": content_unlocked
                    })
                    
                    # Record verified transaction
                    verified_transactions[receipt.transaction_id] = {
                        "product_id": receipt.product_id,
                        "user_id": request.user_id,
                        "content_unlocked": content_unlocked,
                        "verified_at": datetime.now().isoformat(),
                        "platform": receipt.platform
                    }
                else:
                    failed_restorations.append({
                        "product_id": receipt.product_id,
                        "transaction_id": receipt.transaction_id,
                        "error": verification_result.get("error", "Verification failed")
                    })
                    
            except Exception as e:
                logger.error(f"Error restoring purchase {receipt.transaction_id}: {e}")
                failed_restorations.append({
                    "product_id": receipt.product_id,
                    "transaction_id": receipt.transaction_id,
                    "error": str(e)
                })
        
        logger.info(f"Restored {len(restored_products)} purchases for user {request.user_id}")
        
        return {
            "success": True,
            "user_id": request.user_id,
            "restored_count": len(restored_products),
            "failed_count": len(failed_restorations),
            "restored_products": restored_products,
            "failed_restorations": failed_restorations,
            "message": f"Successfully restored {len(restored_products)} purchases"
        }
        
    except Exception as e:
        logger.error(f"Error restoring purchases for user {request.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore purchases: {str(e)}"
        )

@router.get("/user/{user_id}/premium-content", response_model=PremiumContentResponse)
async def get_user_premium_content(
    user_id: str,
    include_expired: bool = False
) -> PremiumContentResponse:
    """
    Get user's current premium content and subscription status.
    """
    try:
        logger.info(f"Getting premium content for user {user_id}")
        
        user_data = user_purchases.get(user_id, {})
        
        # Check subscription status
        subscription_active = False
        subscription_expires_at = None
        premium_tier = "free"
        
        if "subscriptions" in user_data:
            for sub_id, sub_data in user_data["subscriptions"].items():
                if sub_data.get("active", False):
                    expires_at = sub_data.get("expires_at")
                    if expires_at:
                        expires_at = datetime.fromisoformat(expires_at)
                        if expires_at > datetime.now():
                            subscription_active = True
                            subscription_expires_at = expires_at
                            if sub_id == "snake_classic_pro":
                                premium_tier = "pro"
                            break
        
        # Get owned content
        owned_themes = user_data.get("themes", [])
        owned_powerups = user_data.get("powerups", [])
        owned_cosmetics = user_data.get("cosmetics", [])
        
        # Battle pass status
        battle_pass_active = False
        battle_pass_expires_at = None
        battle_pass_tier = 0
        
        if "battle_pass" in user_data:
            bp_data = user_data["battle_pass"]
            expires_at = bp_data.get("expires_at")
            if expires_at:
                expires_at = datetime.fromisoformat(expires_at)
                if expires_at > datetime.now():
                    battle_pass_active = True
                    battle_pass_expires_at = expires_at
                    battle_pass_tier = bp_data.get("tier", 0)
        
        # Tournament entries
        tournament_entries = user_data.get("tournament_entries", {})
        
        return PremiumContentResponse(
            user_id=user_id,
            premium_tier=premium_tier,
            subscription_active=subscription_active,
            subscription_expires_at=subscription_expires_at,
            owned_themes=owned_themes,
            owned_powerups=owned_powerups,
            owned_cosmetics=owned_cosmetics,
            battle_pass_active=battle_pass_active,
            battle_pass_expires_at=battle_pass_expires_at,
            battle_pass_tier=battle_pass_tier,
            tournament_entries=tournament_entries
        )
        
    except Exception as e:
        logger.error(f"Error getting premium content for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get premium content: {str(e)}"
        )

@router.post("/webhook/google-play")
async def google_play_webhook(background_tasks: BackgroundTasks, request_data: Dict[str, Any]):
    """
    Handle Google Play purchase webhooks for subscription updates.
    """
    try:
        logger.info("Received Google Play webhook")
        
        # In production, verify the webhook signature
        # if not _verify_google_play_signature(request_data):
        #     raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Process the webhook data
        message_data = request_data.get("message", {})
        if "data" in message_data:
            # Decode base64 data
            decoded_data = base64.b64decode(message_data["data"]).decode('utf-8')
            notification_data = json.loads(decoded_data)
            
            # Handle subscription notifications
            if "subscriptionNotification" in notification_data:
                background_tasks.add_task(
                    _handle_subscription_webhook,
                    notification_data["subscriptionNotification"]
                )
            
            # Handle one-time product notifications
            if "oneTimeProductNotification" in notification_data:
                background_tasks.add_task(
                    _handle_product_webhook,
                    notification_data["oneTimeProductNotification"]
                )
        
        return {"success": True, "message": "Webhook processed"}
        
    except Exception as e:
        logger.error(f"Error processing Google Play webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )

@router.post("/webhook/app-store")
async def app_store_webhook(background_tasks: BackgroundTasks, request_data: Dict[str, Any]):
    """
    Handle Apple App Store purchase webhooks for subscription updates.
    """
    try:
        logger.info("Received App Store webhook")
        
        # In production, verify the webhook signature
        # if not _verify_app_store_signature(request_data):
        #     raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Process App Store Server Notifications
        notification_type = request_data.get("notificationType")
        
        if notification_type:
            background_tasks.add_task(
                _handle_app_store_webhook,
                notification_type,
                request_data
            )
        
        return {"success": True, "message": "Webhook processed"}
        
    except Exception as e:
        logger.error(f"Error processing App Store webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )

# Helper functions

async def _verify_with_app_store(receipt: PurchaseReceipt) -> Dict[str, Any]:
    """
    Verify purchase receipt with the appropriate app store.
    
    In production, this would make actual API calls to:
    - Google Play Developer API for Android
    - App Store Server API for iOS
    """
    try:
        if receipt.platform.lower() == "android":
            # Verify with Google Play
            # This is a mock implementation
            logger.info(f"Verifying Android purchase: {receipt.product_id}")
            return {
                "valid": True,
                "product_id": receipt.product_id,
                "transaction_id": receipt.transaction_id
            }
        elif receipt.platform.lower() == "ios":
            # Verify with App Store
            # This is a mock implementation
            logger.info(f"Verifying iOS purchase: {receipt.product_id}")
            return {
                "valid": True,
                "product_id": receipt.product_id,
                "transaction_id": receipt.transaction_id
            }
        else:
            return {
                "valid": False,
                "error": f"Unsupported platform: {receipt.platform}"
            }
    except Exception as e:
        logger.error(f"Error verifying with app store: {e}")
        return {
            "valid": False,
            "error": str(e)
        }

def _determine_premium_content(product_id: str) -> List[str]:
    """Determine what premium content to unlock based on product ID."""
    content_mapping = {
        # Individual themes
        "crystal_theme": ["theme_crystal"],
        "cyberpunk_theme": ["theme_cyberpunk"],
        "space_theme": ["theme_space"],
        "ocean_theme": ["theme_ocean"],
        "desert_theme": ["theme_desert"],
        
        # Theme bundle
        "premium_themes_bundle": [
            "theme_crystal", "theme_cyberpunk", "theme_space", 
            "theme_ocean", "theme_desert"
        ],
        
        # Power-ups
        "mega_powerups": ["powerup_mega_speed", "powerup_mega_invincibility", "powerup_mega_score", "powerup_mega_slow"],
        "exclusive_powerups": ["powerup_teleport", "powerup_size_reducer", "powerup_score_shield"],
        "powerups_bundle": [
            "powerup_mega_speed", "powerup_mega_invincibility", "powerup_mega_score", 
            "powerup_mega_slow", "powerup_teleport", "powerup_size_reducer", "powerup_score_shield"
        ],
        
        # Cosmetics
        "golden_snake": ["skin_golden"],
        "rainbow_snake": ["skin_rainbow"],
        "galaxy_snake": ["skin_galaxy"],
        "dragon_snake": ["skin_dragon"],
        "premium_trails": ["trail_particle", "trail_glow", "trail_rainbow", "trail_fire"],
        "cosmetics_bundle": [
            "skin_golden", "skin_rainbow", "skin_galaxy", "skin_dragon",
            "trail_particle", "trail_glow", "trail_rainbow", "trail_fire"
        ],
        
        # Subscriptions (handled separately)
        "snake_classic_pro": ["subscription_pro"],
        "battle_pass_season": ["battle_pass"],
        
        # Tournament entries
        "tournament_bronze": ["tournament_entry_bronze"],
        "tournament_silver": ["tournament_entry_silver"],
        "tournament_gold": ["tournament_entry_gold"],
        "championship_entry": ["tournament_entry_championship"],
    }
    
    return content_mapping.get(product_id, [])

def _is_subscription_product(product_id: str) -> bool:
    """Check if a product is a subscription."""
    subscription_products = {"snake_classic_pro", "battle_pass_season"}
    return product_id in subscription_products

async def _handle_subscription(receipt: PurchaseReceipt) -> SubscriptionInfo:
    """Handle subscription products."""
    expires_at = None
    auto_renewing = True
    
    if receipt.product_id == "snake_classic_pro":
        # Pro subscription - 1 month
        expires_at = datetime.now() + timedelta(days=30)
    elif receipt.product_id == "battle_pass_season":
        # Battle pass - 60 days
        expires_at = datetime.now() + timedelta(days=60)
        auto_renewing = False  # Battle pass doesn't auto-renew
    
    return SubscriptionInfo(
        product_id=receipt.product_id,
        is_active=True,
        expires_at=expires_at,
        auto_renewing=auto_renewing,
        original_transaction_id=receipt.transaction_id
    )

async def _update_user_premium_status(
    user_id: str,
    product_id: str,
    transaction_id: str,
    content_unlocked: List[str]
) -> None:
    """Update user's premium status and content."""
    if user_id not in user_purchases:
        user_purchases[user_id] = {
            "themes": [],
            "powerups": [],
            "cosmetics": [],
            "subscriptions": {},
            "battle_pass": {},
            "tournament_entries": {},
            "purchase_history": []
        }
    
    user_data = user_purchases[user_id]
    
    # Add to purchase history
    user_data["purchase_history"].append({
        "product_id": product_id,
        "transaction_id": transaction_id,
        "purchased_at": datetime.now().isoformat(),
        "content_unlocked": content_unlocked
    })
    
    # Unlock content
    for content in content_unlocked:
        if content.startswith("theme_"):
            theme_name = content.replace("theme_", "")
            if theme_name not in user_data["themes"]:
                user_data["themes"].append(theme_name)
        
        elif content.startswith("powerup_"):
            if content not in user_data["powerups"]:
                user_data["powerups"].append(content)
        
        elif content.startswith("skin_") or content.startswith("trail_"):
            if content not in user_data["cosmetics"]:
                user_data["cosmetics"].append(content)
        
        elif content == "subscription_pro":
            user_data["subscriptions"]["snake_classic_pro"] = {
                "active": True,
                "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
                "auto_renewing": True,
                "original_transaction_id": transaction_id
            }
        
        elif content == "battle_pass":
            user_data["battle_pass"] = {
                "active": True,
                "expires_at": (datetime.now() + timedelta(days=60)).isoformat(),
                "tier": 0,
                "xp": 0,
                "original_transaction_id": transaction_id
            }
        
        elif content.startswith("tournament_entry_"):
            entry_type = content.replace("tournament_entry_", "")
            current_entries = user_data["tournament_entries"].get(entry_type, 0)
            user_data["tournament_entries"][entry_type] = current_entries + 1

async def _log_purchase_analytics(
    user_id: str,
    product_id: str,
    verification_result: Dict[str, Any]
) -> None:
    """Log purchase analytics data."""
    logger.info(f"Purchase analytics: user={user_id}, product={product_id}, valid={verification_result.get('valid', False)}")

async def _handle_subscription_webhook(notification_data: Dict[str, Any]) -> None:
    """Handle subscription webhook notifications."""
    logger.info(f"Processing subscription webhook: {notification_data}")
    # Implement subscription status updates based on webhook data

async def _handle_product_webhook(notification_data: Dict[str, Any]) -> None:
    """Handle one-time product webhook notifications."""
    logger.info(f"Processing product webhook: {notification_data}")
    # Implement product purchase processing based on webhook data

async def _handle_app_store_webhook(notification_type: str, data: Dict[str, Any]) -> None:
    """Handle App Store webhook notifications."""
    logger.info(f"Processing App Store webhook: type={notification_type}")
    # Implement App Store notification processing