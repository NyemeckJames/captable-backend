from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.application.ports.repositories import IShareholderProfileRepository
from app.domain.entities.shareholder_profile import ShareholderProfile
from app.infrastructure.database.models import ShareholderProfileModel
from sqlalchemy.orm import selectinload

from app.infrastructure.database.repositories.base_repository import BaseRepository


class PostgresShareholderProfileRepository(BaseRepository, IShareholderProfileRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
    
    async def save(self, profile: ShareholderProfile) -> ShareholderProfile:
        # Check if exists
        result = await self.session.execute(
            select(ShareholderProfileModel)
            .where(ShareholderProfileModel.id == profile.id)
            .options(selectinload(ShareholderProfileModel.user))
        )
        db_profile = result.scalar_one_or_none()
        
        if db_profile:
            # Update existing
            db_profile.user_id = profile.user_id
            db_profile.name = profile.name
            db_profile.address = profile.address
            db_profile.phone = profile.phone
        else:
            # Create new
            db_profile = ShareholderProfileModel(
                id=profile.id,
                user_id=profile.user_id,
                name=profile.name,
                address=profile.address,
                phone=profile.phone
            )
            self.session.add(db_profile)
        
        await self.session.commit()
        # Recharger avec la relation user préchargée pour éviter le lazy load
        result = await self.session.execute(
            select(ShareholderProfileModel)
            .where(ShareholderProfileModel.id == db_profile.id)
            .options(selectinload(ShareholderProfileModel.user))
        )
        db_profile = result.scalar_one_or_none()
        
        return self._to_domain(db_profile)
    
    async def find_by_id(self, profile_id: UUID) -> Optional[ShareholderProfile]:
        """Recherche async-safe avec gestion d'erreurs"""
        
        async def _find_operation():
            result = await self.session.execute(
                select(ShareholderProfileModel)
                .where(ShareholderProfileModel.id == profile_id)
                .options(selectinload(ShareholderProfileModel.user))  # Préchargement
            )
            db_profile = result.scalar_one_or_none()
            
            if db_profile:
                return self._to_domain(db_profile)
            return None
        
        return await self._execute_query(_find_operation)
    
    async def find_by_user_id(self, user_id: UUID) -> Optional[ShareholderProfile]:
        result = await self.session.execute(
            select(ShareholderProfileModel)
            .where(ShareholderProfileModel.user_id == user_id)
            .options(selectinload(ShareholderProfileModel.user))
        )
        db_profile = result.scalar_one_or_none()
        
        if db_profile:
            return self._to_domain(db_profile)
        return None
    
    async def find_all(self) -> List[ShareholderProfile]:
        result = await self.session.execute(
            select(ShareholderProfileModel).options(selectinload(ShareholderProfileModel.user))
        )
        db_profiles = result.scalars().all()
        
        return [self._to_domain(db_profile) for db_profile in db_profiles]
    
    def _to_domain(self, db_profile: ShareholderProfileModel) -> ShareholderProfile:
        # Ajout de l'email du user si chargé
        email = None
        if hasattr(db_profile, "user") and db_profile.user is not None:
            email = getattr(db_profile.user, "email", None)
        domain_obj = ShareholderProfile(
            id=db_profile.id,
            user_id=db_profile.user_id,
            name=db_profile.name,
            address=db_profile.address,
            phone=db_profile.phone
        )
        if email:
            domain_obj.email = email
        return domain_obj
