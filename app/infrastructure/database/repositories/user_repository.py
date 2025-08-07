from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.application.ports.repositories import IUserRepository
from app.domain.entities.user import User
from app.domain.value_objects.email import Email
from app.infrastructure.database.models import UserModel


class PostgresUserRepository(IUserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save(self, user: User) -> User:
        # Check if exists
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user.id)
        )
        db_user = result.scalar_one_or_none()
        
        if db_user:
            # Update existing
            db_user.email = user.email.value
            db_user.hashed_password = user.hashed_password
            db_user.role = user.role
            db_user.is_active = user.is_active
        else:
            # Create new
            db_user = UserModel(
                id=user.id,
                email=user.email.value,
                hashed_password=user.hashed_password,
                role=user.role,
                is_active=user.is_active
            )
            self.session.add(db_user)
        
        await self.session.commit()
        await self.session.refresh(db_user)
        
        return self._to_domain(db_user)
    
    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        db_user = result.scalar_one_or_none()
        
        if db_user:
            return self._to_domain(db_user)
        return None
    
    async def find_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        db_user = result.scalar_one_or_none()
        
        if db_user:
            return self._to_domain(db_user)
        return None
    
    async def find_all(self) -> List[User]:
        result = await self.session.execute(select(UserModel))
        db_users = result.scalars().all()
        
        return [self._to_domain(db_user) for db_user in db_users]
    
    def _to_domain(self, db_user: UserModel) -> User:
        return User(
            id=db_user.id,
            email=Email(db_user.email),
            hashed_password=db_user.hashed_password,
            role=db_user.role,
            is_active=db_user.is_active
        )
