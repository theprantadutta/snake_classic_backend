"""
Purchase service for managing in-app purchases
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.purchase import Purchase
from app.models.user import User, UserPremiumContent
from app.schemas.purchase import PurchaseReceipt, PremiumContentResponse
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


# Product to content mapping - must match Flutter ProductIds exactly
PRODUCT_CONTENT_MAP = {
    # Premium Themes
    "crystal_theme": ["theme_crystal"],
    "cyberpunk_theme": ["theme_cyberpunk"],
    "space_theme": ["theme_space"],
    "ocean_theme": ["theme_ocean"],
    "desert_theme": ["theme_desert"],
    "forest_theme": ["theme_forest"],
    "premium_themes_bundle": [
        "theme_crystal", "theme_cyberpunk", "theme_space",
        "theme_ocean", "theme_desert", "theme_forest"
    ],

    # Snake Coins (Consumable)
    "coin_pack_small": ["coins_100"],
    "coin_pack_medium": ["coins_550"],  # 500 + 50 bonus
    "coin_pack_large": ["coins_1400"],  # 1200 + 200 bonus
    "coin_pack_mega": ["coins_3000"],   # 2500 + 500 bonus

    # Premium Power-ups
    "mega_powerups_pack": ["powerup_mega_speed", "powerup_mega_shield", "powerup_mega_magnet", "powerup_mega_slowmo"],
    "exclusive_powerups_pack": ["powerup_teleport", "powerup_ghost", "powerup_shrink"],
    "premium_powerups_bundle": [
        "powerup_mega_speed", "powerup_mega_shield", "powerup_mega_magnet", "powerup_mega_slowmo",
        "powerup_teleport", "powerup_ghost", "powerup_shrink"
    ],

    # Snake Skins
    "golden": ["skin_golden"],
    "rainbow": ["skin_rainbow"],
    "galaxy": ["skin_galaxy"],
    "dragon": ["skin_dragon"],
    "electric": ["skin_electric"],
    "fire": ["skin_fire"],
    "ice": ["skin_ice"],
    "shadow": ["skin_shadow"],
    "neon": ["skin_neon"],
    "crystal": ["skin_crystal"],
    "cosmic": ["skin_cosmic"],

    # Trail Effects (prefixed with trail_ to avoid duplicate IDs)
    "trail_particle": ["trail_particle"],
    "trail_glow": ["trail_glow"],
    "trail_rainbow": ["trail_rainbow"],
    "trail_fire": ["trail_fire"],
    "trail_electric": ["trail_electric"],
    "trail_star": ["trail_star"],
    "trail_cosmic": ["trail_cosmic"],
    "trail_neon": ["trail_neon"],
    "trail_shadow": ["trail_shadow"],
    "trail_crystal": ["trail_crystal"],
    "trail_dragon": ["trail_dragon"],

    # Cosmetic Bundles
    "starter_pack": ["skin_golden", "skin_fire", "trail_particle", "trail_glow"],
    "elemental_pack": ["skin_fire", "skin_ice", "skin_electric", "trail_fire", "trail_electric"],
    "cosmic_collection": ["skin_galaxy", "skin_cosmic", "skin_crystal", "trail_cosmic", "trail_crystal", "trail_star"],
    "ultimate_collection": [
        "skin_golden", "skin_rainbow", "skin_galaxy", "skin_dragon", "skin_electric",
        "skin_fire", "skin_ice", "skin_shadow", "skin_neon", "skin_crystal", "skin_cosmic",
        "trail_particle", "trail_glow", "trail_rainbow", "trail_fire", "trail_electric",
        "trail_star", "trail_cosmic", "trail_neon", "trail_shadow", "trail_crystal", "trail_dragon"
    ],

    # Subscriptions
    "snake_classic_pro_monthly": ["subscription_pro"],
    "snake_classic_pro_yearly": ["subscription_pro"],
    "battle_pass_season": ["battle_pass"],

    # Tournament Entries (Consumable)
    "tournament_bronze": ["tournament_entry_bronze"],
    "tournament_silver": ["tournament_entry_silver"],
    "tournament_gold": ["tournament_entry_gold"],
    "championship_entry": ["tournament_entry_championship"],
    "tournament_vip_entry": ["tournament_entry_vip"],
}

SUBSCRIPTION_PRODUCTS = {
    "snake_classic_pro_monthly",
    "snake_classic_pro_yearly",
    "battle_pass_season"
}


class PurchaseService:
    """Service for purchase operations"""

    async def verify_with_store(self, receipt: PurchaseReceipt) -> Dict[str, Any]:
        """
        Verify purchase with app store.
        In production, this would make actual API calls.
        """
        # Mock verification - always returns valid for demo
        # TODO: Implement actual Google Play and App Store verification
        logger.info(f"Verifying {receipt.platform} purchase: {receipt.product_id}")
        return {
            "valid": True,
            "product_id": receipt.product_id,
            "transaction_id": receipt.transaction_id
        }

    def verify_purchase(
        self,
        db: Session,
        user_id: UUID,
        receipt: PurchaseReceipt,
        verification_result: Dict[str, Any]
    ) -> Tuple[Purchase, List[str]]:
        """
        Process a verified purchase and unlock content.
        Returns: (purchase, content_unlocked)
        """
        # Check for duplicate transaction
        existing = db.query(Purchase).filter(
            Purchase.transaction_id == receipt.transaction_id
        ).first()

        if existing:
            return existing, existing.content_unlocked or []

        # Determine content to unlock
        content_unlocked = PRODUCT_CONTENT_MAP.get(receipt.product_id, [])

        # Check if subscription
        is_subscription = receipt.product_id in SUBSCRIPTION_PRODUCTS
        expires_at = None
        auto_renewing = False

        if is_subscription:
            if receipt.product_id == "snake_classic_pro":
                expires_at = utc_now() + timedelta(days=30)
                auto_renewing = True
            elif receipt.product_id == "battle_pass_season":
                expires_at = utc_now() + timedelta(days=60)
                auto_renewing = False

        # Create purchase record
        purchase = Purchase(
            user_id=user_id,
            product_id=receipt.product_id,
            transaction_id=receipt.transaction_id,
            platform=receipt.platform,
            receipt_data=receipt.receipt_data,
            is_verified=verification_result.get("valid", False),
            is_subscription=is_subscription,
            expires_at=expires_at,
            auto_renewing=auto_renewing,
            content_unlocked=content_unlocked,
            purchase_timestamp=receipt.purchase_time,
            verified_at=utc_now()
        )
        db.add(purchase)

        # Update user's premium content
        self._update_premium_content(db, user_id, receipt.product_id, content_unlocked, expires_at)

        db.commit()
        db.refresh(purchase)

        return purchase, content_unlocked

    def _update_premium_content(
        self,
        db: Session,
        user_id: UUID,
        product_id: str,
        content_unlocked: List[str],
        expires_at: Optional[datetime]
    ):
        """Update user's premium content based on purchase"""
        # Get or create premium content record
        premium = db.query(UserPremiumContent).filter(
            UserPremiumContent.user_id == user_id
        ).first()

        if not premium:
            premium = UserPremiumContent(
                user_id=user_id,
                premium_tier="free",
                subscription_active=False,
                battle_pass_active=False,
                owned_themes=[],
                owned_powerups=[],
                owned_cosmetics=[],
                tournament_entries={},
                coins=0
            )
            db.add(premium)

        # Process each content item
        for content in content_unlocked:
            if content.startswith("theme_"):
                theme = content.replace("theme_", "")
                if theme not in (premium.owned_themes or []):
                    themes = list(premium.owned_themes or [])
                    themes.append(theme)
                    premium.owned_themes = themes

            elif content.startswith("powerup_"):
                if content not in (premium.owned_powerups or []):
                    powerups = list(premium.owned_powerups or [])
                    powerups.append(content)
                    premium.owned_powerups = powerups

            elif content.startswith("skin_") or content.startswith("trail_"):
                if content not in (premium.owned_cosmetics or []):
                    cosmetics = list(premium.owned_cosmetics or [])
                    cosmetics.append(content)
                    premium.owned_cosmetics = cosmetics

            elif content == "subscription_pro":
                premium.premium_tier = "pro"
                premium.subscription_active = True
                premium.subscription_expires_at = expires_at

            elif content == "battle_pass":
                premium.battle_pass_active = True
                premium.battle_pass_expires_at = expires_at
                premium.battle_pass_tier = 0

            elif content.startswith("tournament_entry_"):
                entry_type = content.replace("tournament_entry_", "")
                entries = dict(premium.tournament_entries or {})
                entries[entry_type] = entries.get(entry_type, 0) + 1
                premium.tournament_entries = entries

            elif content.startswith("coins_"):
                amount_str = content.replace("coins_", "")
                try:
                    amount = int(amount_str)
                    premium.coins = (premium.coins or 0) + amount
                except ValueError:
                    pass

    def get_user_premium_content(
        self,
        db: Session,
        user_id: UUID
    ) -> PremiumContentResponse:
        """Get user's premium content status"""
        premium = db.query(UserPremiumContent).filter(
            UserPremiumContent.user_id == user_id
        ).first()

        if not premium:
            return PremiumContentResponse(
                user_id=user_id,
                premium_tier="free",
                subscription_active=False,
                battle_pass_active=False,
                battle_pass_tier=0,
                owned_themes=[],
                owned_powerups=[],
                owned_cosmetics=[],
                coins=0
            )

        # Check if subscriptions are still active
        now = utc_now()
        subscription_active = (
            premium.subscription_active and
            premium.subscription_expires_at and
            premium.subscription_expires_at > now
        )
        battle_pass_active = (
            premium.battle_pass_active and
            premium.battle_pass_expires_at and
            premium.battle_pass_expires_at > now
        )

        return PremiumContentResponse(
            user_id=user_id,
            premium_tier=premium.premium_tier if subscription_active else "free",
            subscription_active=subscription_active,
            subscription_expires_at=premium.subscription_expires_at if subscription_active else None,
            battle_pass_active=battle_pass_active,
            battle_pass_tier=premium.battle_pass_tier or 0,
            owned_themes=premium.owned_themes or [],
            owned_powerups=premium.owned_powerups or [],
            owned_cosmetics=premium.owned_cosmetics or [],
            coins=premium.coins or 0
        )

    def get_user_purchases(
        self,
        db: Session,
        user_id: UUID
    ) -> List[Purchase]:
        """Get user's purchase history"""
        return db.query(Purchase).filter(
            Purchase.user_id == user_id
        ).order_by(Purchase.created_at.desc()).all()


purchase_service = PurchaseService()
