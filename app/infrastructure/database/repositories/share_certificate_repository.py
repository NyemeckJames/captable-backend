from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.application.ports.repositories import IShareCertificateRepository
from app.domain.entities.share_certificate import ShareCertificate
from app.infrastructure.database.models import ShareCertificateModel


class PostgresShareCertificateRepository(IShareCertificateRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save(self, certificate: ShareCertificate) -> ShareCertificate:
        """Sauvegarde async-safe d'un certificat"""
        try:
            # Check if exists
            result = await self.session.execute(
                select(ShareCertificateModel).where(ShareCertificateModel.id == certificate.id)
            )
            db_certificate = result.scalar_one_or_none()
            
            if db_certificate:
                # Update existing
                db_certificate.share_issuance_id = certificate.share_issuance_id
                db_certificate.watermark = certificate.watermark
                db_certificate.storage_path = certificate.storage_path
                db_certificate.generation_date = certificate.generation_date
            else:
                # Create new
                db_certificate = ShareCertificateModel(
                    id=certificate.id,
                    share_issuance_id=certificate.share_issuance_id,
                    watermark=certificate.watermark,
                    storage_path=certificate.storage_path,
                    generation_date=certificate.generation_date
                )
                self.session.add(db_certificate)
            
            await self.session.commit()
            await self.session.refresh(db_certificate)
            
            return self._to_domain(db_certificate)
            
        except Exception as e:
            await self.session.rollback()
            raise Exception(f"Failed to save certificate: {str(e)}")
    
    async def find_by_issuance_id(self, issuance_id: UUID) -> Optional[ShareCertificate]:
        """Recherche d'un certificat par issuance_id"""
        try:
            result = await self.session.execute(
                select(ShareCertificateModel)
                .where(ShareCertificateModel.share_issuance_id == issuance_id)
            )
            db_certificate = result.scalar_one_or_none()
            
            if db_certificate:
                return self._to_domain(db_certificate)
            return None
            
        except Exception as e:
            raise Exception(f"Failed to find certificate: {str(e)}")
    
    async def find_by_id(self, certificate_id: UUID) -> Optional[ShareCertificate]:
        """Recherche d'un certificat par ID"""
        try:
            result = await self.session.execute(
                select(ShareCertificateModel)
                .where(ShareCertificateModel.id == certificate_id)
            )
            db_certificate = result.scalar_one_or_none()
            
            if db_certificate:
                return self._to_domain(db_certificate)
            return None
            
        except Exception as e:
            raise Exception(f"Failed to find certificate by id: {str(e)}")
    
    def _to_domain(self, db_certificate: ShareCertificateModel) -> ShareCertificate:
        """Conversion vers entité domaine"""
        return ShareCertificate(
            id=db_certificate.id,
            share_issuance_id=db_certificate.share_issuance_id,
            watermark=db_certificate.watermark,
            storage_path=db_certificate.storage_path,
            generation_date=db_certificate.generation_date
        )
