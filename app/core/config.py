from __future__ import annotations

import secrets
from typing import Annotated, Any

from pydantic import AnyHttpUrl, BeforeValidator, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> list[str]:
    if isinstance(v, str):
        import json
        try:
            return json.loads(v)
        except Exception:
            return [i.strip() for i in v.split(",")]
    return v


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "FastFacebook CRM"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: Annotated[list[str], BeforeValidator(parse_cors)] = ["*"]
    ALLOWED_ORIGINS: Annotated[list[str], BeforeValidator(parse_cors)] = [
        "http://localhost:3000"
    ]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/fastfacebook"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CELERY_BROKER: str = "redis://localhost:6379/1"
    REDIS_CELERY_BACKEND: str = "redis://localhost:6379/2"

    # JWT
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Encryption
    ENCRYPTION_KEY: str = ""

    # Facebook
    FACEBOOK_APP_ID: str = ""
    FACEBOOK_APP_SECRET: str = ""
    FACEBOOK_API_VERSION: str = "v21.0"
    FACEBOOK_WEBHOOK_VERIFY_TOKEN: str = secrets.token_urlsafe(32)
    FACEBOOK_REDIRECT_URI: str = "https://lethargy-football-eccentric.ngrok-free.dev/api/v1/auth/facebook/callback"

    # WhatsApp
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Celery
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_TASK_SOFT_TIME_LIMIT: int = 300
    CELERY_TASK_TIME_LIMIT: int = 600

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    CORS_ALLOW_CREDENTIALS: bool = True

    @property
    def facebook_oauth_url(self) -> str:
        return (
            f"https://www.facebook.com/{self.FACEBOOK_API_VERSION}/dialog/oauth"
            f"?client_id={self.FACEBOOK_APP_ID}"
            f"&redirect_uri={self.FACEBOOK_REDIRECT_URI}"
            "&scope=public_profile,pages_show_list,pages_read_engagement,pages_manage_ads,"
            "ads_management,ads_read,business_management,leads_retrieval"
            "&response_type=code"
        )

    @property
    def facebook_graph_base_url(self) -> str:
        return f"https://graph.facebook.com/{self.FACEBOOK_API_VERSION}"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


settings = Settings()
