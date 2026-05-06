from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@db:5432/social_automation"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # AI providers
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3"
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "meta-llama/llama-3-8b-instruct:free"

    # Reddit API (optional — falls back to mock)
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: str = "SocialAutomationBot/1.0"

    # Twitter/X (optional — mock if absent)
    twitter_bearer_token: Optional[str] = None

    # TikTok (optional — mock if absent)
    tiktok_api_key: Optional[str] = None

    # Publisher tokens (optional)
    instagram_access_token: Optional[str] = None
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_token_secret: Optional[str] = None

    # App
    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
