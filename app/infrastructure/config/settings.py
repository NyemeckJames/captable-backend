from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Obligatoire : chargée depuis .env
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    database_url: str
    company_name: str
    company_authorized_shares: int

    # Initialisation de l'admin
    admin_email: str
    admin_password: str
    admin_role: str
    admin_name: str
    
    db_host: str
    db_port: str
    db_user: str
    db_password: str

    # Facultatif (tu peux garder une valeur par défaut ici si besoin)
    debug: bool = True

    class Config:
        env_file = ".env"


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
