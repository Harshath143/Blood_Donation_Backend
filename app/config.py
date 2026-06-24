from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_NAME: str = "LifeDrop API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Database — Railway injects DATABASE_URL automatically
    DATABASE_URL: str          # postgresql+asyncpg://user:pass@host/db
    SYNC_DATABASE_URL: str     # postgresql://user:pass@host/db  (psycopg2 for large objects)
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 5

    # Redis — Railway injects REDIS_URL automatically
    REDIS_URL: str
    REDIS_CACHE_TTL: int = 300

    # Security
    SECRET_KEY: str            # 64-char random hex — generate with: openssl rand -hex 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # SMTP Email (open-source, works with Gmail / Zoho / Brevo free tier)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str         # Gmail: use App Password, not your login password
    SMTP_USE_TLS: bool = True
    FROM_EMAIL: str = "noreply@lifedrop.in"
    FROM_NAME: str = "LifeDrop"

    # CORS — Netlify frontend URL
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "https://lifedrop.netlify.app"
    ]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    EMERGENCY_RATE_LIMIT_PER_MINUTE: int = 10
    AUTH_RATE_LIMIT_PER_MINUTE: int = 10

    # Geolocation
    MAX_DONOR_SEARCH_RADIUS_KM: int = 100
    DEFAULT_SEARCH_RADIUS_KM: int = 25

    # OTP
    OTP_EXPIRE_SECONDS: int = 600    # 10 minutes

    # File upload limits
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024  # 5MB

    # Sentry (optional — free tier available)
    SENTRY_DSN: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

@lru_cache()
def get_settings() -> Settings:
    return Settings()
