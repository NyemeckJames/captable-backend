from typing import List
from uuid import UUID
from app.application.queries.dashboard_queries import (
    GetAdminDashboardQuery
)
from app.application.dtos.dashboard_dtos import (
    AdminDashboardDto,
    ShareholderSummaryDto,
    IssuanceDto,
    IssuanceSummaryDTO
)
from app.application.ports.repositories import (
    IShareholderRepository,
    ICompanyRepository,
    IShareIssuanceRepository,
    IShareholderProfileRepository,
    IUserRepository
)
from app.domain.exceptions import DomainException
from app.domain.entities.share_issuance import ShareIssuance
from app.application.queries.certificate_queries import GetIssuanceForCertificateQuery
from app.application.queries.audit_queries import GetAuditEventsQuery
from app.application.dtos.audit_dtos import AuditEventDTO

class GetAdminDashboardHandler:
    def __init__(
        self,
        shareholder_repository: IShareholderRepository,
        company_repository: ICompanyRepository,
        issuance_repository: IShareIssuanceRepository
    ):
        self.shareholder_repository = shareholder_repository
        self.company_repository = company_repository
        self.issuance_repository = issuance_repository
    
    async def handle(self, query: GetAdminDashboardQuery) -> AdminDashboardDto:
        # Get company info
        company = await self.company_repository.find_the_company()
        if not company:
            raise DomainException("Company not found")
        
        # Get all shareholders
        shareholders = await self.shareholder_repository.find_all()
        
        # Get all issuances for calculating totals
        all_issuances = await self.issuance_repository.find_all()
        
        # Build shareholder summaries
        shareholder_summaries = []
        for shareholder in shareholders:
            # Calculate total shares and value for this shareholder
            shareholder_issuances = [
                issuance for issuance in all_issuances 
                if issuance.shareholder_profile_id == shareholder.id
            ]
            
            total_shares = sum(issuance.quantity.value for issuance in shareholder_issuances)
            total_value = sum(
                issuance.total_value.amount for issuance in shareholder_issuances
            )
            
            shareholder_summaries.append(ShareholderSummaryDto(
                profile_id=shareholder.id,
                user_id=getattr(shareholder, "user_id", None),
                name=shareholder.name,
                email=shareholder.email.value,
                total_shares=total_shares,
                total_value=total_value
            ))
        
        return AdminDashboardDto(
            shareholders=shareholder_summaries,
            total_issued_shares=company.issued_shares.value,
            total_authorized_shares=company.authorized_shares.value,
            company_name=company.name
        )




# --- NEW HANDLER FOR GET /api/issuances/ ---
class GetIssuancesHandler:
    def __init__(
        self, 
        issuance_repository: IShareIssuanceRepository, 
        profile_repository: IShareholderProfileRepository,  # CHANGÉ: profile au lieu de shareholder
        user_repository: IUserRepository  # AJOUTÉ: pour les admins
    ):
        self.issuance_repository = issuance_repository
        self.profile_repository = profile_repository  # CORRIGÉ
        self.user_repository = user_repository  # AJOUTÉ

    async def handle(self, user: dict) -> List[IssuanceSummaryDTO]:
        if user["role"] == "admin":
            # 👑 ADMIN: Voir TOUTES les émissions
            return await self._handle_admin_view()
        else:
            # 👤 SHAREHOLDER: Voir SEULEMENT ses propres émissions
            return await self._handle_shareholder_view(user["id"])
    
    async def _handle_admin_view(self) -> List[IssuanceSummaryDTO]:
        """Vue admin : toutes les émissions avec noms des shareholders"""
        
        # 1️⃣ Récupérer TOUTES les émissions
        issuances = await self.issuance_repository.find_all()
        
        # 2️⃣ Récupérer TOUS les profils shareholders (pour les noms)
        profiles = await self.profile_repository.find_all()
        
        # 3️⃣ Créer un dictionnaire de lookup: {profile_id: nom}
        profile_names = {profile.id: profile.name for profile in profiles}
        
        # 4️⃣ Transformer chaque émission en DTO
        return [
            IssuanceSummaryDTO(
                id=issuance.id,
                shareholder_profile_id=issuance.shareholder_profile_id,
                shareholder_name=profile_names.get(
                    issuance.shareholder_profile_id, 
                    "Unknown Profile"
                ),
                share_class_id=issuance.share_class_id,
                quantity=issuance.quantity.value,
                price_per_share=issuance.price_per_share.amount,
                total_value=issuance.total_value.amount,
                issue_date=issuance.issue_date
            )
            for issuance in issuances
        ]
    
    async def _handle_shareholder_view(self, user_id: str) -> List[IssuanceSummaryDTO]:
        """Vue shareholder : seulement ses propres émissions"""
        
        print(f"Looking for shareholder profile for user_id: {user_id}")
        
        # 1️⃣ Trouver le profil shareholder associé à ce user_id
        profile = await self.profile_repository.find_by_user_id(UUID(user_id))
        if not profile:
            raise DomainException(f"No shareholder profile found for user {user_id}")
        
        print(f"Found shareholder profile: {profile.id} (name: {profile.name})")
        
        # 2️⃣ Récupérer SEULEMENT les émissions de ce profil
        issuances = await self.issuance_repository.find_by_shareholder_profile_id(profile.id)
        
        print(f"Found {len(issuances)} issuances for profile {profile.id}")
        
        # 3️⃣ Transformer en DTO avec le nom du profil
        return [
            IssuanceSummaryDTO(
                id=issuance.id,
                shareholder_profile_id=issuance.shareholder_profile_id,
                shareholder_name=profile.name,  # Nom direct du profil
                share_class_id=issuance.share_class_id,
                quantity=issuance.quantity.value,
                price_per_share=issuance.price_per_share.amount,
                total_value=issuance.total_value.amount,
                issue_date=issuance.issue_date
            )
            for issuance in issuances
        ]


# --- NEW HANDLER FOR GET /api/shareholders/ ---
from app.application.queries.dashboard_queries import GetAllShareholdersQuery
from app.application.dtos.dashboard_dtos import ShareholderSummaryDTO

class GetAllShareholdersHandler:
    def __init__(self, shareholder_repository: IShareholderRepository):
        self.shareholder_repository = shareholder_repository

    async def handle(self, query: GetAllShareholdersQuery) -> List[ShareholderSummaryDTO]:
        shareholders = await self.shareholder_repository.get_all_with_total_shares()
        return [ShareholderSummaryDTO(**sh) for sh in shareholders]

class GetAuditEventsHandler:
    def __init__(self, get_audit_events_query: GetAuditEventsQuery):
        self.get_audit_events_query = get_audit_events_query

    async def handle(self, limit: int = 100, offset: int = 0) -> list[AuditEventDTO]:
        return await self.get_audit_events_query.execute(limit=limit, offset=offset)
