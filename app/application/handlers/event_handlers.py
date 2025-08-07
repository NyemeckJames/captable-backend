from app.domain.events.share_events import ShareIssuanceCompleted, CertificateGenerated
from app.application.ports.repositories import IShareIssuanceRepository, IShareCertificateRepository
from app.application.ports.pdf_generator import IPdfGenerator
from app.application.ports.event_publisher import IEventPublisher


class PdfGenerationListener:
    def __init__(
        self,
        issuance_repository: IShareIssuanceRepository,
        certificate_repository: IShareCertificateRepository,
        pdf_generator: IPdfGenerator,
        event_publisher: IEventPublisher
    ):
        self.issuance_repository = issuance_repository
        self.certificate_repository = certificate_repository
        self.pdf_generator = pdf_generator
        self.event_publisher = event_publisher
    
    async def handle_share_issuance_completed(self, event: ShareIssuanceCompleted):
        # Load the issuance
        issuance = await self.issuance_repository.find_by_id(event.issuance_id)
        if not issuance:
            return  # Log error in real implementation
        
        # Generate PDF certificate
        certificate = await self.pdf_generator.generate_share_certificate(issuance)
        
        # Save certificate
        await self.certificate_repository.save(certificate)
        
        # Update issuance with certificate reference
        issuance.certificate_id = certificate.id
        await self.issuance_repository.save(issuance)
        
        # Publish certificate generated event
        certificate_event = CertificateGenerated(
            certificate.id,
            issuance.id,
            certificate.storage_path
        )
        await self.event_publisher.publish(certificate_event)
