from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.api.auth.jwt_handler import verify_token
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.repositories.user_repository import PostgresUserRepository

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise credentials_exception

    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception

    # Get user from database
    user_repo = PostgresUserRepository(db)
    user = await user_repo.find_by_email(email)

    if user is None or not user.is_active:
        raise credentials_exception

    return {
        "id": str(user.id),
        "email": user.email.value,
        "role": user.role
    }


async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_shareholder_user(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") not in ["admin", "shareholder"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_user_with_role(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Dependency that returns the current user (admin or shareholder) without filtering by role.
    """
    return await get_current_user(credentials, db)
