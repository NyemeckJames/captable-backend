from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.application.ports.repositories import IShareholderRepository
from app.domain.entities.shareholder import Shareholder
from app.domain.value_objects.email import Email
from app.infrastructure.database.models import ShareholderProfileModel, ShareIssuanceModel


class PostgresShareholderRepository(IShareholderRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_with_total_shares(self):
        from sqlalchemy import func
        result = await self.session.execute(
            select(
                ShareholderProfileModel.id,
                ShareholderProfileModel.name,
                ShareholderProfileModel.user_id,
                func.coalesce(func.sum(ShareIssuanceModel.quantity), 0).label("total_shares")
            )
            .outerjoin(ShareIssuanceModel, ShareholderProfileModel.id == ShareIssuanceModel.shareholder_profile_id)
            .group_by(ShareholderProfileModel.id)
        )
        rows = result.all()
        # Fetch user email and role for each shareholder
        shareholders = []
        for row in rows:
            shareholder_id, name, user_id, total_shares = row
            # Fetch user info
            user_result = await self.session.execute(
                select(ShareholderProfileModel)
                .options(selectinload(ShareholderProfileModel.user))
                .where(ShareholderProfileModel.id == shareholder_id)
            )
            db_shareholder = user_result.scalar_one_or_none()
            email = db_shareholder.user.email if db_shareholder and db_shareholder.user else ""
            role = db_shareholder.user.role if db_shareholder and db_shareholder.user else "shareholder"
            shareholders.append({
                "id": shareholder_id,
                "name": name,
                "email": email,
                "role": role,
                "total_shares": total_shares
            })
        return shareholders

    
    async def save(self, shareholder: Shareholder) -> Shareholder:
        # Check if exists
        result = await self.session.execute(
            select(ShareholderProfileModel).where(ShareholderProfileModel.id == shareholder.id)
        )
        db_shareholder = result.scalar_one_or_none()
        
        if db_shareholder:
            # Update existing
            db_shareholder.name = shareholder.name
            # Email and role are on the related user, update if needed
            if db_shareholder.user:
                db_shareholder.user.email = shareholder.email.value
                db_shareholder.user.role = shareholder.role
        else:
            # Create new
            # Requires a related UserModel to be created separately
            db_shareholder = ShareholderProfileModel(
                id=shareholder.id,
                name=shareholder.name
            )
            self.session.add(db_shareholder)
        
        await self.session.commit()
        await self.session.refresh(db_shareholder)
        
        return self._to_domain(db_shareholder)
    
    async def find_by_id(self, shareholder_id: UUID) -> Optional[Shareholder]:
        result = await self.session.execute(
            select(ShareholderProfileModel).where(ShareholderProfileModel.id == shareholder_id)
        )
        db_shareholder = result.scalar_one_or_none()
        
        if db_shareholder:
            return self._to_domain(db_shareholder)
        return None
    
    async def find_all(self) -> List[Shareholder]:
        result = await self.session.execute(
            select(ShareholderProfileModel).options(selectinload(ShareholderProfileModel.user))
        )
        db_shareholders = result.scalars().all()
        
        return [self._to_domain(db_sh) for db_sh in db_shareholders]
    
    async def find_by_email(self, email: str) -> Optional[Shareholder]:
        result = await self.session.execute(
            select(ShareholderProfileModel).join(ShareholderProfileModel.user).where(ShareholderProfileModel.user.has(email=email))
        )
        db_shareholder = result.scalar_one_or_none()
        
        if db_shareholder:
            return self._to_domain(db_shareholder)
        return None
    
    def _to_domain(self, db_shareholder: ShareholderProfileModel) -> Shareholder:
        # user may be None if not joined, so handle gracefully
        email = Email(db_shareholder.user.email) if db_shareholder.user else Email("")
        role = db_shareholder.user.role if db_shareholder.user else "shareholder"
        user_id = db_shareholder.user.id if db_shareholder.user else None
        return Shareholder(
            id=db_shareholder.id,
            user_id=user_id,
            name=db_shareholder.name,
            email=email,
            role=role
        )
