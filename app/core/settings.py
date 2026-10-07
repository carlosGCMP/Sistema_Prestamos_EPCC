from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://epcc:epcc@localhost:5432/epcc_prestamos"
    jwt_secret: SecretStr = Field(default=SecretStr("dev-only-not-for-production-secret-32chars"))
    access_token_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.app_env == "production" and len(settings.jwt_secret.get_secret_value()) < 32:
        raise ValueError("JWT_SECRET debe tener al menos 32 caracteres en producción")
    return settings
