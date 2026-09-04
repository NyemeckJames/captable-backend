import logging
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
from app.domain.exceptions import AccessDeniedException, DomainException

logger = logging.getLogger(__name__)


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

    async def authorize_issuance_access(
        self,
        issuance_id: UUID,
        requesting_user_id: UUID,
        requesting_user_role: str
    ) -> ShareIssuance:
        """Public entry point for the scope check.

        Every route that exposes an issuance or anything derived from it must call
        this before reading, generating or returning the resource. Keeping the check
        here rather than in the routes is what prevents a new branch in a handler
        from silently bypassing it.
        """
        return await self._get_and_validate_issuance(
            issuance_id, requesting_user_id, requesting_user_role
        )

    async def generate_certificate_for_issuance(
        self,
        issuance_id: UUID,
        requesting_user_id: UUID,
        requesting_user_role: str
    ) -> ShareCertificate:
        """Return the certificate for an issuance, generating it on first request."""
        issuance = await self._get_and_validate_issuance(
            issuance_id, requesting_user_id, requesting_user_role
        )

        existing_certificate = await self.certificate_repository.find_by_issuance_id(issuance_id)
        if existing_certificate:
            logger.debug("Certificate already exists for issuance %s", issuance_id)
            return existing_certificate

        try:
            # PDF generation is synchronous by design: WeasyPrint is CPU bound and
            # gains nothing from being awaited.
            certificate = self.pdf_generator.generate_share_certificate(issuance)
            saved_certificate = await self.certificate_repository.save(certificate)

            event = CertificateGenerated(
                certificate_id=saved_certificate.id,
                issuance_id=issuance_id,
                storage_path=saved_certificate.storage_path
            )
            await self.event_publisher.publish(event)

            logger.info("Generated certificate %s for issuance %s", saved_certificate.id, issuance_id)
            return saved_certificate

        except Exception as exc:
            logger.exception("Certificate generation failed for issuance %s", issuance_id)
            raise DomainException("Failed to generate certificate") from exc

    async def regenerate_pdf(self, issuance_id: UUID, certificate: ShareCertificate) -> ShareCertificate:
        """Rebuild the PDF of an existing certificate whose file went missing.

        Callers must have passed `authorize_issuance_access` first: this method
        performs no scope check of its own.
        """
        issuance = await self.issuance_repository.find_by_id(issuance_id)
        if not issuance:
            raise DomainException(f"Issuance {issuance_id} not found")

        regenerated = self.pdf_generator.generate_share_certificate(issuance)
        certificate.storage_path = regenerated.storage_path
        saved = await self.certificate_repository.save(certificate)
        logger.info("Regenerated missing PDF for certificate %s", saved.id)
        return saved

    async def _get_and_validate_issuance(
        self,
        issuance_id: UUID,
        requesting_user_id: UUID,
        requesting_user_role: str
    ) -> ShareIssuance:
        """Resolve the issuance and check that the caller is inside its perimeter."""
        issuance = await self.issuance_repository.find_by_id(issuance_id)
        if not issuance:
            raise DomainException(f"Issuance {issuance_id} not found")

        if requesting_user_role == "admin":
            return issuance

        profile = await self.profile_repository.find_by_id(issuance.shareholder_profile_id)
        if not profile:
            raise DomainException("Shareholder profile not found for this issuance")

        if profile.user_id != requesting_user_id:
            logger.warning(
                "Denied access to issuance %s for user %s", issuance_id, requesting_user_id
            )
            raise AccessDeniedException(
                "Access denied. You can only access certificates for your own shares."
            )

        return issuance
