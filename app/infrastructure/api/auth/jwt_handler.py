from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.infrastructure.config.settings import get_settings
from sqlalchemy import select

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None

from app.infrastructure.database.connection import AsyncSessionLocal
from app.infrastructure.database.models import UserModel
from sqlalchemy.orm import joinedload
from sqlalchemy import func

async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserModel)
            .options(joinedload(UserModel.shareholder_profile))  # Charger la relation shareholder_profile
            .where(func.lower(UserModel.email) == username.lower())
        )
        db_user = result.scalar_one_or_none()

        if not db_user:
            return None

        if not verify_password(password, db_user.hashed_password):
            return None

        user_data = {
            "id": str(db_user.id),
            "username": db_user.email,
            "role": db_user.role,
            "name": db_user.email  # par défaut
        }
        print(f"Authenticated user: {db_user.shareholder_profile}")

        # Si c'est un actionnaire, ajouter les infos métiers du shareholder
        if db_user.role == "shareholder" and db_user.shareholder_profile:
            user_data["shareholder"] = {
                "name": db_user.shareholder_profile.name,
                "address": db_user.shareholder_profile.address,
                "phone": db_user.shareholder_profile.phone
            }

        return user_data
