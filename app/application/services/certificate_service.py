# app/application/services/certificate_service.py (VERSION 100% SYNCHRONE)
from uuid import UUID
from app.application.ports.repositories import (
    IShareIssuanceRepository, 
    IShareholderProfileRepository,
    IUserRepository,
    IShareCertificateRepository
)
from app.application.ports.pdf_generator import IPdfGenerator
from app.application.ports.event_publisher import IEventPublisher
from app.domain.entities.share_issuance import ShareIssuance
from app.domain.entities.share_certificate import ShareCertificate
from app.domain.events.share_events import CertificateGenerated
from app.domain.exceptions import DomainException


class CertificateGenerationService:
    def __init__(
        self,
        issuance_repository: IShareIssuanceRepository,
        profile_repository: IShareholderProfileRepository,
        user_repository: IUserRepository,
        certificate_repository: IShareCertificateRepository,
        pdf_generator: IPdfGenerator,
        event_publisher: IEventPublisher
    ):
        self.issuance_repository = issuance_repository
        self.profile_repository = profile_repository
        self.user_repository = user_repository
        self.certificate_repository = certificate_repository
        self.pdf_generator = pdf_generator
        self.event_publisher = event_publisher
    
    async def generate_certificate_for_issuance(
        self, 
        issuance_id: UUID, 
        requesting_user_id: UUID, 
        requesting_user_role: str
    ) -> ShareCertificate:
        """
        Service principal - ASYNC pour DB, SYNC pour PDF
        """
        print(f"Starting certificate generation for issuance {issuance_id}")
        
        # 1. ASYNC: Récupérer et valider l'issuance (DB calls)
        issuance = await self._get_and_validate_issuance(
            issuance_id, requesting_user_id, requesting_user_role
        )
        print(f"Validated issuance: {issuance.id}")
        
        # 2. ASYNC: Vérifier si un certificat existe déjà (DB call)
        existing_certificate = await self.certificate_repository.find_by_issuance_id(issuance_id)
        if existing_certificate:
            print(f"Certificate already exists: {existing_certificate.id}")
            return existing_certificate
        
        # 3. SYNC: Générer le certificat PDF (NO ASYNCIO!)
        try:
            print(f"Generating PDF certificate synchronously...")
            
            # ✅ APPEL DIRECT SYNCHRONE - PAS D'ASYNCIO
            certificate = self.pdf_generator.generate_share_certificate(issuance)
            
            print(f"PDF generated successfully: {certificate.id}")
            
            # 4. ASYNC: Sauvegarder le certificat (DB call)
            saved_certificate = await self.certificate_repository.save(certificate)
            print(f"Certificate saved to database: {saved_certificate.id}")
            
            # 5. ASYNC: Publier l'événement (DB/messaging)
            event = CertificateGenerated(
                certificate_id=saved_certificate.id,
                issuance_id=issuance_id,
                storage_path=saved_certificate.storage_path
            )
            await self.event_publisher.publish(event)
            print(f"Published CertificateGenerated event")
            
            return saved_certificate
            
        except Exception as e:
            print(f"Error during certificate generation: {str(e)}")
            raise DomainException(f"Failed to generate certificate: {str(e)}")
    
    async def _get_and_validate_issuance(
        self, 
        issuance_id: UUID, 
        requesting_user_id: UUID, 
        requesting_user_role: str
    ) -> ShareIssuance:
        """Validation et contrôle d'accès pour l'issuance"""
        
        print(f"Validating issuance {issuance_id} for user {requesting_user_id} (role: {requesting_user_role})")
        
        # ASYNC: Récupérer l'issuance (DB call)
        issuance = await self.issuance_repository.find_by_id(issuance_id)
        if not issuance:
            raise DomainException(f"Issuance {issuance_id} not found")
        
        # Contrôle d'accès
        if requesting_user_role != "admin":
            print(f"Non-admin user, checking profile ownership")
            
            # ASYNC: Pour un shareholder, vérifier l'appartenance (DB call)
            profile = await self.profile_repository.find_by_id(issuance.shareholder_profile_id)
            if not profile:
                raise DomainException("Shareholder profile not found for this issuance")
                
            if profile.user_id != requesting_user_id:
                raise DomainException("Access denied. You can only generate certificates for your own shares.")
            
            print(f"Access granted: profile {profile.id} belongs to user {requesting_user_id}")
        else:
            print(f"Admin access granted")
        
        return issuance