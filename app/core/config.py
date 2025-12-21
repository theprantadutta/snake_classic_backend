"""
Application Configuration for Snake Classic Backend
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Get the project root directory (where .env file is located)
PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Database Configuration
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "snake_classic"
    DATABASE_USERNAME: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"  # Default for development

    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components"""
        return (
            f"postgresql://{self.DATABASE_USERNAME}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    # JWT Configuration
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"  # Default for development
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Firebase Configuration
    FIREBASE_PROJECT_ID: str = "snake-classic-2a376"
    GOOGLE_APPLICATION_CREDENTIALS: str = "firebase-admin-sdk.json"

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8393
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Snake Classic API"
    DEBUG: bool = True

    # CORS Configuration
    ALLOWED_ORIGINS: str = "*"

    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Parse CORS origins from string"""
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # Environment
    ENVIRONMENT: str = "development"

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

    # Backwards compatibility aliases (old firebase_service uses lowercase)
    @property
    def google_application_credentials(self) -> str:
        return self.GOOGLE_APPLICATION_CREDENTIALS

    @property
    def firebase_project_id(self) -> str:
        return self.FIREBASE_PROJECT_ID


# Global settings instance
settings = Settings()