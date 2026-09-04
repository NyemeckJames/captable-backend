from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Required, loaded from .env. No defaults on purpose: a missing secret must
    # stop the application at boot rather than fall back to a known value.
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    database_url: str
    company_name: str
    company_authorized_shares: int

    # Credentials of the bootstrap admin, consumed by scripts/seed_admin.py only.
    admin_email: str
    admin_password: str
    admin_role: str
    admin_name: str

    db_host: str
    db_port: str
    db_user: str
    db_password: str

    # Operational switches. Defaults are the safe ones: anything that widens the
    # exposed surface has to be turned on explicitly.
    environment: str = "production"
    debug: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    class Config:
        env_file = ".env"


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
