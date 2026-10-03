from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Multi-user To-Do API"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://todo:todo@db:5432/todo"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "todo-api"
    jwt_audience: str = "todo-client"
    access_token_expire_minutes: int = 30
    task_cache_ttl_seconds: int = 300
    task_list_cache_ttl_seconds: int = 60
    rate_limit_requests: int = 300
    auth_rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 60

    @field_validator("jwt_secret")
    @classmethod
    def reject_placeholder_secret(cls, value: str) -> str:
        insecure_values = ("replace-this", "development-only", "change-me")
        if any(marker in value.lower() for marker in insecure_values):
            raise ValueError("JWT_SECRET must be a randomly generated secret")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
