"""
Purchase API endpoints
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.purchase import (
    PurchaseVerifyRequest,
    PurchaseVerifyResponse,
    PurchaseResponse,
    RestorePurchasesRequest,
    RestorePurchasesResponse,
    PremiumContentResponse,
)
from app.services.purchase_service import purchase_service

router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.post("/verify", response_model=PurchaseVerifyResponse)
async def verify_purchase(
    request: PurchaseVerifyRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify a purchase receipt"""
    # Verify with app store
    verification_result = await purchase_service.verify_with_store(request.receipt)

    if not verification_result.get("valid"):
        return PurchaseVerifyResponse(
            success=False,
            valid=False,
            product_id=request.receipt.product_id,
            transaction_id=request.receipt.transaction_id,
            error_message=verification_result.get("error", "Verification failed")
        )

    # Process the purchase
    purchase, content_unlocked = purchase_service.verify_purchase(
        db, current_user.id, request.receipt, verification_result
    )

    return PurchaseVerifyResponse(
        success=True,
        valid=True,
        product_id=purchase.product_id,
        transaction_id=purchase.transaction_id,
        content_unlocked=content_unlocked,
        is_subscription=purchase.is_subscription,
        expires_at=purchase.expires_at
    )


@router.post("/restore", response_model=RestorePurchasesResponse)
async def restore_purchases(
    request: RestorePurchasesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restore previous purchases"""
    restored_products = []
    failed_restorations = []

    for receipt in request.receipts:
        try:
            verification_result = await purchase_service.verify_with_store(receipt)

            if verification_result.get("valid"):
                purchase, content_unlocked = purchase_service.verify_purchase(
                    db, current_user.id, receipt, verification_result
                )
                restored_products.append({
                    "product_id": purchase.product_id,
                    "transaction_id": purchase.transaction_id,
                    "content_unlocked": content_unlocked
                })
            else:
                failed_restorations.append({
                    "product_id": receipt.product_id,
                    "transaction_id": receipt.transaction_id,
                    "error": verification_result.get("error", "Verification failed")
                })
        except Exception as e:
            failed_restorations.append({
                "product_id": receipt.product_id,
                "transaction_id": receipt.transaction_id,
                "error": str(e)
            })

    return RestorePurchasesResponse(
        restored_count=len(restored_products),
        failed_count=len(failed_restorations),
        restored_products=restored_products,
        failed_restorations=failed_restorations
    )


@router.get("/premium-content", response_model=PremiumContentResponse)
async def get_my_premium_content(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's premium content"""
    return purchase_service.get_user_premium_content(db, current_user.id)


@router.get("/user/{user_id}/premium-content", response_model=PremiumContentResponse)
async def get_user_premium_content(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a user's premium content"""
    from uuid import UUID
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )
    return purchase_service.get_user_premium_content(db, uid)


@router.get("/history", response_model=List[PurchaseResponse])
async def get_purchase_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's purchase history"""
    purchases = purchase_service.get_user_purchases(db, current_user.id)
    return [PurchaseResponse.model_validate(p) for p in purchases]


@router.post("/webhook/google-play")
async def google_play_webhook(
    request_data: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Handle Google Play webhook notifications"""
    # In production, verify webhook signature
    # Process subscription updates, refunds, etc.
    return {"success": True, "message": "Webhook received"}


@router.post("/webhook/app-store")
async def app_store_webhook(
    request_data: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Handle App Store webhook notifications"""
    # In production, verify webhook signature
    # Process subscription updates, refunds, etc.
    return {"success": True, "message": "Webhook received"}
