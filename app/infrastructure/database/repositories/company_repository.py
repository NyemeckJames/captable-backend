
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.application.ports.repositories import ICompanyRepository
from app.domain.entities.company import Company, ShareClass
from app.domain.value_objects.share_quantity import ShareQuantity
from app.infrastructure.database.models import CompanyModel, ShareClassModel
import json


class PostgresCompanyRepository(ICompanyRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save(self, company: Company) -> Company:
        """Sauvegarde avec gestion async-safe et optimisée"""
        try:
            # Check if company exists avec préchargement des share classes
            result = await self.session.execute(
                select(CompanyModel)
                .options(selectinload(CompanyModel.share_classes))  # Préchargement
                .where(CompanyModel.id == company.id)
            )
            db_company = result.scalar_one_or_none()
            
            if db_company:
                # Update existing company
                db_company.name = company.name
                db_company.authorized_shares = company.authorized_shares.value
                db_company.issued_shares = company.issued_shares.value
            else:
                # Create new company
                db_company = CompanyModel(
                    id=company.id,
                    name=company.name,
                    authorized_shares=company.authorized_shares.value,
                    issued_shares=company.issued_shares.value
                )
                self.session.add(db_company)
                
                # Il faut d'abord flusher pour obtenir l'ID si c'est une nouvelle company
                await self.session.flush()
            
            # Gestion des share classes de manière optimisée
            await self._sync_share_classes(company, db_company.id)
            
            # Commit final
            await self.session.commit()
            await self.session.refresh(db_company)
            
            return company
            
        except Exception as e:
            await self.session.rollback()
            raise Exception(f"Failed to save company: {str(e)}")
    
    async def _sync_share_classes(self, company: Company, company_db_id):
        """Synchronisation optimisée des share classes"""
        # Récupérer toutes les share classes existantes en une seule requête
        result = await self.session.execute(
            select(ShareClassModel).where(ShareClassModel.company_id == company_db_id)
        )
        existing_classes = {db_class.id: db_class for db_class in result.scalars().all()}
        
        # Traiter chaque share class du domaine
        for share_class in company.share_classes:
            if share_class.id in existing_classes:
                # Update existing
                db_class = existing_classes[share_class.id]
                db_class.name = share_class.name
                db_class.type = share_class.type
                db_class.rights = json.dumps(share_class.rights)
            else:
                # Create new
                db_class = ShareClassModel(
                    id=share_class.id,
                    company_id=company_db_id,
                    name=share_class.name,
                    type=share_class.type,
                    rights=json.dumps(share_class.rights)
                )
                self.session.add(db_class)
    
    async def find_the_company(self) -> Optional[Company]:
        """Recherche optimisée avec préchargement des relations"""
        try:
            # Requête optimisée avec préchargement
            result = await self.session.execute(
                select(CompanyModel)
                .options(selectinload(CompanyModel.share_classes))
                .limit(1)
            )
            db_company = result.scalar_one_or_none()
            
            if not db_company:
                return None
            
            # Conversion vers entité domaine avec relations préchargées
            share_classes = []
            if hasattr(db_company, 'share_classes') and db_company.share_classes:
                share_classes = [
                    ShareClass(
                        id=db_class.id,
                        name=db_class.name,
                        type=db_class.type,
                        rights=json.loads(db_class.rights or '{}')
                    )
                    for db_class in db_company.share_classes
                ]
            
            return Company(
                id=db_company.id,
                name=db_company.name,
                authorized_shares=ShareQuantity(db_company.authorized_shares),
                issued_shares=ShareQuantity(db_company.issued_shares),
                share_classes=share_classes
            )
            
        except Exception as e:
            raise Exception(f"Failed to find company: {str(e)}")


