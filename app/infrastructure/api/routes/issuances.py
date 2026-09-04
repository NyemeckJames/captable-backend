import logging
import os
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, conint
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.commands.issuance_commands import CreateIssuanceCommand
from app.application.dtos.dashboard_dtos import IssuanceSummaryDTO
from app.application.handlers.command_handlers import CreateIssuanceHandler
from app.application.handlers.query_handlers import GetIssuancesHandler
from app.application.services.audit_service import AuditService
from app.application.services.certificate_service import CertificateGenerationService
from app.domain.entities.audit_event import AuditActionType, AuditEntityType
from app.domain.exceptions import AccessDeniedException, DomainException
from app.infrastructure.api.auth.dependencies import get_admin_user, get_shareholder_user
from app.infrastructure.api.dependencies import get_audit_service
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.repositories.company_repository import PostgresCompanyRepository
from app.infrastructure.database.repositories.issuance_repository import PostgresShareIssuanceRepository
from app.infrastructure.database.repositories.share_certificate_repository import PostgresShareCertificateRepository
from app.infrastructure.database.repositories.shareholder_profile_repository import PostgresShareholderProfileRepository
from app.infrastructure.database.repositories.user_repository import PostgresUserRepository
from app.infrastructure.services.email_service import ConsoleEmailService
from app.infrastructure.services.event_service import InMemoryEventPublisher
from app.infrastructure.services.pdf_service import WeasyPrintPdfGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/issuances", tags=["Issuances"])


class CreateIssuanceRequest(BaseModel):
    shareholder_id: UUID
    share_class_id: str
    quantity: conint(gt=0)
    price_per_share: Decimal
    currency: str = "EUR"
    issue_date: Optional[date] = None


def _build_certificate_service(db: AsyncSession) -> CertificateGenerationService:
    return CertificateGenerationService(
        issuance_repository=PostgresShareIssuanceRepository(db),
        profile_repository=PostgresShareholderProfileRepository(db),
        user_repository=PostgresUserRepository(db),
        certificate_repository=PostgresShareCertificateRepository(db),
        pdf_generator=WeasyPrintPdfGenerator(),
        event_publisher=InMemoryEventPublisher()
    )


def _pdf_response(issuance_id: UUID, storage_path: str) -> FileResponse:
    filename = f"share_certificate_{issuance_id}.pdf"
    return FileResponse(
        path=storage_path,
        filename=filename,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get(
    "/",
    response_model=List[IssuanceSummaryDTO],
    summary="Lister les émissions d'actions",
    description="Retourne la liste des émissions d'actions. L'admin voit toutes les émissions, un actionnaire ne voit que les siennes.",
    tags=["Issuances"],
    responses={
        200: {
            "description": "Liste des émissions d'actions retournée avec succès",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "a1b2c3d4-e5f6-7890-1234-56789abcdef0",
                            "shareholder_id": "550e8400-e29b-41d4-a716-446655440000",
                            "share_class_id": "ordinary",
                            "quantity": 100,
                            "price_per_share": "1.5",
                            "currency": "EUR",
                            "issue_date": "2024-01-01"
                        }
                    ]
                }
            }
        },
        401: {"description": "Non autorisé (token requis)"},
        422: {"description": "Erreur de validation des données"}
    },
    openapi_extra={"security": [{"BearerAuth": []}]}
)
async def get_issuances(
    current_user: dict = Depends(get_shareholder_user),
    db: AsyncSession = Depends(get_db)
):
    """Get issuances: all of them for an admin, only their own for a shareholder."""
    handler = GetIssuancesHandler(
        issuance_repository=PostgresShareIssuanceRepository(db),
        profile_repository=PostgresShareholderProfileRepository(db),
        user_repository=PostgresUserRepository(db)
    )

    try:
        return await handler.handle(current_user)
    except DomainException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        logger.exception("Unexpected error while listing issuances")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.post(
    "/",
    response_model=dict,
    summary="Créer une émission d'actions",
    description="Crée une nouvelle émission d'actions pour un actionnaire donné. Réservé à l'admin.",
    tags=["Issuances"],
    responses={
        200: {
            "description": "Émission créée avec succès",
            "content": {
                "application/json": {
                    "example": {
                        "issuance_id": "a1b2c3d4-e5f6-7890-1234-56789abcdef0",
                        "message": "Issuance created successfully"
                    }
                }
            }
        },
        400: {"description": "Erreur métier (ex: actionnaire inexistant)"},
        401: {"description": "Non autorisé (admin requis)"},
        422: {"description": "Erreur de validation des données"}
    },
    openapi_extra={"security": [{"BearerAuth": []}]}
)
async def create_issuance(
    request: CreateIssuanceRequest,
    current_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    http_request: Request = None,
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Crée une nouvelle émission d'actions pour un actionnaire donné (admin uniquement).

    - **shareholder_id** : UUID du profil actionnaire
    - **share_class_id** : Identifiant de la classe d'actions (ex : "ordinary")
    - **quantity** : Nombre d'actions à émettre
    - **price_per_share** : Prix unitaire de l'action
    - **currency** : Devise (ex : "EUR")
    - **issue_date** : Date d'émission (optionnelle)
    """
    try:
        handler = CreateIssuanceHandler(
            company_repository=PostgresCompanyRepository(db),
            shareholder_repository=PostgresShareholderProfileRepository(db),
            issuance_repository=PostgresShareIssuanceRepository(db),
            event_publisher=InMemoryEventPublisher(),
            email_service=ConsoleEmailService()
        )

        command = CreateIssuanceCommand(
            shareholder_profile_id=request.shareholder_id,
            share_class_id=request.share_class_id,
            quantity=request.quantity,
            price_per_share=request.price_per_share,
            currency=request.currency,
            issue_date=request.issue_date
        )

        result = await handler.handle(command)

        try:
            await audit_service.log_event(
                action_type=AuditActionType.SHARE_ISSUANCE_CREATED,
                user_id=current_user["id"],
                target_entity_type=AuditEntityType.SHARE_ISSUANCE,
                target_entity_id=result.get("issuance_id"),
                event_metadata={
                    "shareholder_id": str(request.shareholder_id),
                    "quantity": request.quantity,
                    "price_per_share": str(request.price_per_share),
                    "currency": request.currency
                },
                ip_address=http_request.client.host if http_request and http_request.client else "",
                user_agent=http_request.headers.get("user-agent", "") if http_request else ""
            )
        except Exception:
            # An audit write must never swallow a successful issuance, but it must
            # be visible in the logs when it fails.
            logger.exception("Audit log failed for issuance %s", result.get("issuance_id"))

        return result

    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except DomainException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        logger.exception("Unexpected error while creating an issuance")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get(
    "/{issuance_id}/certificate/",
    summary="Télécharger le certificat PDF d'une émission",
    description="Génère et retourne le certificat PDF pour une émission d'actions donnée. Accessible à l'actionnaire concerné ou à l'admin.",
    responses={
        200: {
            "description": "Certificat PDF généré et retourné avec succès",
            "content": {
                "application/pdf": {
                    "schema": {"type": "string", "format": "binary"},
                    "example": "Fichier PDF binaire"
                }
            }
        },
        401: {"description": "Non autorisé (token requis)"},
        403: {"description": "Hors périmètre (émission appartenant à un autre actionnaire)"},
        404: {"description": "Émission ou certificat introuvable"},
        422: {"description": "Erreur de validation des données"}
    },
    openapi_extra={"security": [{"BearerAuth": []}]}
)
async def generate_and_download_certificate(
    issuance_id: UUID,
    current_user: dict = Depends(get_shareholder_user),
    db: AsyncSession = Depends(get_db)
):
    """Return the PDF certificate of an issuance the caller is entitled to."""
    certificate_service = _build_certificate_service(db)
    certificate_repo = PostgresShareCertificateRepository(db)

    try:
        # Scope check first, unconditionally. Every branch below returns a document
        # derived from this issuance, so none of them may run before this succeeds.
        await certificate_service.authorize_issuance_access(
            issuance_id=issuance_id,
            requesting_user_id=UUID(current_user["id"]),
            requesting_user_role=current_user["role"]
        )

        certificate = await certificate_repo.find_by_issuance_id(issuance_id)

        if certificate is None:
            certificate = await certificate_service.generate_certificate_for_issuance(
                issuance_id=issuance_id,
                requesting_user_id=UUID(current_user["id"]),
                requesting_user_role=current_user["role"]
            )
        elif not certificate.storage_path or not os.path.exists(certificate.storage_path):
            certificate = await certificate_service.regenerate_pdf(issuance_id, certificate)

        if not certificate.storage_path or not os.path.exists(certificate.storage_path):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Certificate file could not be produced"
            )

        return _pdf_response(issuance_id, certificate.storage_path)

    except AccessDeniedException as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except DomainException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error while serving certificate for issuance %s", issuance_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the certificate"
        )


@router.get(
    "/{issuance_id}/certificate/info/",
    summary="Métadonnées du certificat d'une émission",
    description="Retourne les métadonnées du certificat sans générer ni télécharger le fichier. Accessible à l'actionnaire concerné ou à l'admin.",
    responses={
        401: {"description": "Non autorisé (token requis)"},
        403: {"description": "Hors périmètre (émission appartenant à un autre actionnaire)"},
        404: {"description": "Aucun certificat pour cette émission"}
    },
    openapi_extra={"security": [{"BearerAuth": []}]}
)
async def get_certificate_info(
    issuance_id: UUID,
    current_user: dict = Depends(get_shareholder_user),
    db: AsyncSession = Depends(get_db)
):
    """Return certificate metadata, under the same scope check as the download."""
    certificate_service = _build_certificate_service(db)

    try:
        await certificate_service.authorize_issuance_access(
            issuance_id=issuance_id,
            requesting_user_id=UUID(current_user["id"]),
            requesting_user_role=current_user["role"]
        )
    except AccessDeniedException as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except DomainException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    certificate = await PostgresShareCertificateRepository(db).find_by_issuance_id(issuance_id)
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No certificate found for this issuance"
        )

    return {
        "certificate_id": str(certificate.id),
        "issuance_id": str(certificate.share_issuance_id),
        "watermark": certificate.watermark,
        "generation_date": certificate.generation_date.isoformat(),
        "file_exists": os.path.exists(certificate.storage_path) if certificate.storage_path else False
    }
