from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-only-secret-change-me-dev-only-secret-change-me"  # noqa: S105  (dev-only placeholder, rejected in production)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"  # development | test | production
    database_url: str = "postgresql+psycopg://aven:aven@localhost:5432/aven"
    secret_key: str = DEV_SECRET
    access_token_minutes: int = 60
    # Lets anyone create a new organization. Fine for dev and pilots you control;
    # turn it off (ALLOW_ORG_SIGNUP=false) once real customers are onboarded by you.
    allow_org_signup: bool = True
    cors_origins: str = "http://localhost:3000"

    @model_validator(mode="after")
    def _reject_weak_secret_in_production(self) -> "Settings":
        if self.env == "production" and (self.secret_key == DEV_SECRET or len(self.secret_key) < 32):
            raise ValueError("SECRET_KEY must be set to a unique value of 32+ characters in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
