from pydantic_settings import BaseSettings
from typing import Dict, Any, List, Optional
from pydantic import validator

class Settings(BaseSettings):
    """Manages application configuration using Pydantic."""

    # Core settings loaded from environment variables
    DATABASE_URL: str = "sqlite:///./music_legends.db"
    DISCORD_TOKEN: str
    DISCORD_APPLICATION_ID: int
    TEST_SERVER_ID: Optional[int] = None
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Payment Gateway Keys
    STRIPE_SECRET_KEY: str = "your_stripe_secret_key"
    STRIPE_WEBHOOK_SECRET: str = "your_stripe_webhook_secret"
    PAYPAL_CLIENT_ID: str = "your_paypal_client_id"
    PAYPAL_CLIENT_SECRET: str = "your_paypal_client_secret"
    PAYPAL_WEBHOOK_ID: Optional[str] = None

    # Webhook Security
    REQUIRE_WEBHOOK_SIGNATURE: bool = True

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 5000
    FLASK_DEBUG: bool = False

    # Rate limiting configuration
    # Merged from rate_config.py and cogs/rate_limiting_system.py
    RATES: Dict[str, Dict[str, Any]] = {
        # From rate_config.py
        "drop": {"limit": 1, "window": 1800},  # 30 min
        "grab": {"limit": 5, "window": 10},  # 10 sec
        "trade": {"limit": 20, "window": 60},  # 1 min

        # From cogs/rate_limiting_system.py (and renaming pack to pack_create)
        "pack_create": {"limit": 5, "window": 3600},  # 5 packs per hour
        "pack_purchase": {"limit": 10, "window": 86400},  # 10 packs per day
        "payment": {"limit": 5, "window": 3600},  # 5 payments per hour
        "api_call": {"limit": 100, "window": 60},  # 100 calls per minute
        "login_attempt": {"limit": 10, "window": 900},  # 10 attempts per 15 minutes
        "failed_login": {"limit": 5, "window": 900},  # 5 failures per 15 minutes
    }

    # Revenue and VIP Configuration
    VIP_MONTHLY_PRICE_USD: float = 9.99
    VIP_BENEFITS: Dict[str, Any] = {
        "trading_fee_reduction": 0.5, # 50% reduction
        "exclusive_packs": ["vip_black", "vip_gold"],
        "battle_bonus_xp": 0.1, # 10% bonus
        "battle_bonus_gold": 0.1, # 10% bonus
    }

    # Battle Pass Configuration
    BATTLE_PASS_PREMIUM_PRICE_USD: float = 19.99
    BATTLE_PASS_SEASON_DURATION_DAYS: int = 30
    BATTLE_PASS_TOTAL_TIERS: int = 50

    # External API Keys
    AUDIODB_API_KEY: str = '1'
    YOUTUBE_API_KEY: str | None = None

    # Development
    DEV_USER_IDS: Optional[List[int]] = []
    DEV_CHANNEL_ID: int | None = None

    @validator('DEV_USER_IDS', pre=True)
    def _parse_dev_user_ids(cls, v: Any) -> list[int]:
        if isinstance(v, (int, float)):
            return [int(v)]
        if isinstance(v, str):
            # Split by comma, strip whitespace, filter out empty strings, and convert to int
            return [int(item.strip()) for item in v.split(',') if item.strip()]
        return v

    # Monitoring
    WEBHOOK_OPS: Optional[str] = None
    WEBHOOK_ECON: Optional[str] = None
    DEV_WEBHOOK_URL: Optional[str] = None

    # Railway
    RAILWAY_ENVIRONMENT: Optional[str] = None
    POSTGRES_BACKUP_URL: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # LastFM
    LASTFM_API_KEY: Optional[str] = None
    LASTFM_SHARED_SECRET: Optional[str] = None

    # NFT Entitlement
    MUSIC_LEGENDS_NFT_CONTRACT: str = "0x0000000000000000000000000000000000000000"
    SAMURAI_FRENCHIE_NFT_CONTRACT: str = "0x0000000000000000000000000000000000000000"
    ALCHEMY_API_KEY: str = ""
    MORALIS_API_KEY: str = ""

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
