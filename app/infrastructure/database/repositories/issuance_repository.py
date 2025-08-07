from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from app.application.ports.repositories import IShareIssuanceRepository
from app.domain.entities.share_issuance import ShareIssuance
from app.domain.exceptions import DomainException
from app.domain.value_objects.share_quantity import ShareQuantity
from app.domain.value_objects.money import Money
from app.infrastructure.database.models import ShareIssuanceModel, ShareholderProfileModel


class PostgresShareIssuanceRepository(IShareIssuanceRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save(self, issuance: ShareIssuance) -> ShareIssuance:
        """Version corrigée sans lazy loading dans _to_domain"""
        # Check if exists
        result = await self.session.execute(
            select(ShareIssuanceModel)
            .options(selectinload(ShareIssuanceModel.certificate))  # Préchargement
            .where(ShareIssuanceModel.id == issuance.id)
        )
        db_issuance = result.scalar_one_or_none()
        
        if db_issuance:
            # Update existing
            db_issuance.shareholder_profile_id = issuance.shareholder_profile_id
            db_issuance.share_class_id = issuance.share_class_id
            db_issuance.quantity = issuance.quantity.value
            db_issuance.price_per_share = issuance.price_per_share.amount
            db_issuance.currency = issuance.price_per_share.currency
            db_issuance.issue_date = issuance.issue_date
        else:
            # Create new
            db_issuance = ShareIssuanceModel(
                id=issuance.id,
                shareholder_profile_id=issuance.shareholder_profile_id,
                share_class_id=issuance.share_class_id,
                quantity=issuance.quantity.value,
                price_per_share=issuance.price_per_share.amount,
                currency=issuance.price_per_share.currency,
                issue_date=issuance.issue_date
            )
            self.session.add(db_issuance)
        
        await self.session.commit()
        
        # IMPORTANT: Recharger avec les relations pour éviter le lazy loading
        await self.session.refresh(db_issuance)
        result = await self.session.execute(
            select(ShareIssuanceModel)
            .options(selectinload(ShareIssuanceModel.certificate))
            .where(ShareIssuanceModel.id == db_issuance.id)
        )
        db_issuance_with_relations = result.scalar_one()
        
        return await self._to_domain_safe(db_issuance_with_relations)
    
    async def find_by_id(self, issuance_id: UUID) -> Optional[ShareIssuance]:
        result = await self.session.execute(
            select(ShareIssuanceModel)
            .options(selectinload(ShareIssuanceModel.certificate))  # Évite lazy loading
            .where(ShareIssuanceModel.id == issuance_id)
        )
        db_issuance = result.scalar_one_or_none()
        
        if db_issuance:
            return await self._to_domain_safe(db_issuance)
        return None
    
    async def find_by_shareholder_profile_id(self, profile_id: UUID) -> List[ShareIssuance]:
        """✅ Méthode correcte - correspond à l'interface"""
        try:
            result = await self.session.execute(
                select(ShareIssuanceModel)
                .options(selectinload(ShareIssuanceModel.certificate))
                .where(ShareIssuanceModel.shareholder_profile_id == profile_id)
                .order_by(ShareIssuanceModel.issue_date.desc())  # 🎯 AJOUT: tri par date
            )
            db_issuances = result.scalars().all()
            
            return [await self._to_domain_safe(db_iss) for db_iss in db_issuances]
            
        except SQLAlchemyError as e:
            raise DomainException(f"Failed to find issuances by profile: {str(e)}")
    
    async def find_all(self) -> List[ShareIssuance]:
        result = await self.session.execute(
            select(ShareIssuanceModel)
            .options(selectinload(ShareIssuanceModel.certificate))
        )
        db_issuances = result.scalars().all()
        
        return [await self._to_domain_safe(db_iss) for db_iss in db_issuances]
    
    async def _to_domain_safe(self, db_issuance: ShareIssuanceModel) -> ShareIssuance:
        """
        Version sécurisée qui évite le lazy loading (ASYNC)
        """
        # Récupérer le certificate_id de manière sécurisée
        certificate_id = None
        try:
            # Vérifier si certificate est chargé (évite lazy loading)
            if hasattr(db_issuance, '__dict__') and 'certificate' in db_issuance.__dict__:
                certificate = db_issuance.__dict__['certificate']
                if certificate is not None:
                    certificate_id = certificate.id
            # Alternative plus sûre : vérifier directement l'attribut
            elif db_issuance.certificate is not None:
                certificate_id = db_issuance.certificate.id
        except Exception:
            # En cas d'erreur, on continue sans certificate_id
            certificate_id = None

        # Récupérer le nom du détenteur à partir de ShareholderProfileModel (ASYNC)
        shareholder_name = None
        try:
            result = await self.session.execute(
                select(ShareholderProfileModel).where(ShareholderProfileModel.id == db_issuance.shareholder_profile_id)
            )
            profile = result.scalar_one_or_none()
            if profile:
                shareholder_name = profile.name
        except Exception:
            shareholder_name = None

        return ShareIssuance(
            id=db_issuance.id,
            shareholder_profile_id=db_issuance.shareholder_profile_id,
            shareholder_name=shareholder_name,
            share_class_id=db_issuance.share_class_id,
            quantity=ShareQuantity(db_issuance.quantity),
            price_per_share=Money(db_issuance.price_per_share, db_issuance.currency),
            issue_date=db_issuance.issue_date,
            certificate_id=certificate_id
        )
