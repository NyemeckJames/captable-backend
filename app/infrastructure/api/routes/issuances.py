from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, conint
from app.domain.exceptions import DomainException
from app.infrastructure.api.auth.dependencies import get_admin_user, get_shareholder_user, get_current_user_with_role
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.repositories.company_repository import PostgresCompanyRepository
from app.infrastructure.database.repositories.shareholder_profile_repository import PostgresShareholderProfileRepository
from app.infrastructure.database.repositories.shareholder_repository import PostgresShareholderRepository
from app.infrastructure.database.repositories.issuance_repository import PostgresShareIssuanceRepository
from app.infrastructure.services.event_service import InMemoryEventPublisher
from app.infrastructure.services.pdf_service import WeasyPrintPdfGenerator
from app.infrastructure.services.email_service import ConsoleEmailService
from app.application.commands.issuance_commands import CreateIssuanceCommand
from app.application.handlers.command_handlers import CreateIssuanceHandler
from app.application.handlers.query_handlers import (
    GetIssuancesHandler
)
from app.infrastructure.api.dependencies import get_audit_service
from app.application.services.audit_service import AuditService
from app.domain.entities.audit_event import AuditActionType, AuditEntityType
from app.application.dtos.dashboard_dtos import IssuanceSummaryDTO
from sqlalchemy.ext.asyncio import AsyncSession
import os

router = APIRouter(prefix="/api/issuances", tags=["Issuances"])


class CreateIssuanceRequest(BaseModel):
    shareholder_id: UUID
    share_class_id: str
    quantity: conint(gt=0)
    price_per_share: Decimal
    currency: str = "EUR"
    issue_date: Optional[date] = None


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
    """Get issuances - all for admin, own for shareholder"""
    
    # REPOSITORIES CORRIGÉS
    issuance_repo = PostgresShareIssuanceRepository(db)
    profile_repo = PostgresShareholderProfileRepository(db)  # CORRIGÉ
    user_repo = PostgresUserRepository(db)  # AJOUTÉ
    
    # HANDLER AVEC LES BONS REPOSITORIES
    handler = GetIssuancesHandler(
        issuance_repository=issuance_repo,
        profile_repository=profile_repo,  # CORRIGÉ
        user_repository=user_repo  # AJOUTÉ
    )
    
    try:
        print(f"Getting issuances for user {current_user['id']} (role: {current_user['role']})")
        result = await handler.handle(current_user)
        print(f"Returning {len(result)} issuances")
        return result
        
    except DomainException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"Unexpected error: {e}")
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

    - **shareholder_id** : UUID du profil actionnaire
    - **share_class_id** : Identifiant de la classe d'actions (ex : "ordinary")
    - **quantity** : Nombre d'actions à émettre
    - **price_per_share** : Prix unitaire de l'action
    - **currency** : Devise (ex : "EUR")
    - **issue_date** : Date d'émission (optionnelle)

    ### Exemple de test (curl) :
    ```
    curl -X POST "http://localhost:8000/api/issuances/" -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"shareholder_id":"<uuid>","share_class_id":"ordinary","quantity":100,"price_per_share":1.5,"currency":"EUR"}'
    ```

    Remplacez `<token>` par le JWT admin et `<uuid>` par l'UUID du profil actionnaire.
    """
    try:
        # Tous les repositories nécessaires
        company_repo = PostgresCompanyRepository(db)        # AJOUTÉ
        shareholder_repo = PostgresShareholderProfileRepository(db)
        issuance_repo = PostgresShareIssuanceRepository(db)
        event_publisher = InMemoryEventPublisher()

        # Handler avec company_repository
        handler = CreateIssuanceHandler(
            company_repository=company_repo,
            shareholder_repository=shareholder_repo,
            issuance_repository=issuance_repo,
            event_publisher=event_publisher,
            email_service=ConsoleEmailService()
        )

        # Commande (inchangée)
        command = CreateIssuanceCommand(
            shareholder_profile_id=request.shareholder_id,
            share_class_id=request.share_class_id,
            quantity=request.quantity,
            price_per_share=request.price_per_share,
            currency=request.currency,
            issue_date=request.issue_date
        )

        print(f"Creating issuance for shareholder {request.shareholder_id}")
        result = await handler.handle(command)

        # Audit log
        try:
            ip_address = http_request.client.host if http_request and http_request.client else ""
            user_agent = http_request.headers.get("user-agent", "") if http_request else ""
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
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as e:
            print(f"Audit log failed: {e}")

        return result

    except (ValueError, TypeError) as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except DomainException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

from app.infrastructure.database.repositories.user_repository import PostgresUserRepository
from app.infrastructure.database.repositories.share_certificate_repository import PostgresShareCertificateRepository
from app.application.services.certificate_service import CertificateGenerationService

@router.get(
    "/{issuance_id}/certificate/",
    summary="Télécharger le certificat PDF d'une émission",
    description="Génère et retourne le certificat PDF pour une émission d'actions donnée. Accessible à l'actionnaire concerné ou à l'admin.",
    responses={
        200: {
            "description": "Certificat PDF généré et retourné avec succès",
            "content": {
                "application/pdf": {
                    "schema": {
                        "type": "string",
                        "format": "binary"
                    },
                    "example": "Fichier PDF binaire"
                }
            }
        },
        400: {"description": "Erreur métier (accès refusé, émission introuvable, etc.)"},
        401: {"description": "Non autorisé (token requis)"},
        404: {"description": "Certificat introuvable"},
        422: {"description": "Erreur de validation des données"}
    },
    openapi_extra={"security": [{"BearerAuth": []}]}
)
async def generate_and_download_certificate(
    issuance_id: UUID,
    current_user: dict = Depends(get_shareholder_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Génère et retourne le certificat PDF pour une émission d'actions donnée.
    """
    print(f"Generating certificate for issuance {issuance_id} by user {current_user['id']}")
    
    # Repositories et services
    issuance_repo = PostgresShareIssuanceRepository(db)
    profile_repo = PostgresShareholderProfileRepository(db)
    user_repo = PostgresUserRepository(db)
    certificate_repo = PostgresShareCertificateRepository(db)
    pdf_generator = WeasyPrintPdfGenerator()
    event_publisher = InMemoryEventPublisher()
    
    # Service de génération de certificat
    certificate_service = CertificateGenerationService(
        issuance_repository=issuance_repo,
        profile_repository=profile_repo,
        user_repository=user_repo,
        certificate_repository=certificate_repo,
        pdf_generator=pdf_generator,
        event_publisher=event_publisher
    )
    
    try:
        # Vérifier si un certificat existe déjà pour cette issuance
        existing_certificate = await certificate_repo.find_by_issuance_id(issuance_id)
        if existing_certificate:
            if existing_certificate.storage_path and os.path.exists(existing_certificate.storage_path):
                print(f"Certificate already exists for issuance {issuance_id}, returning existing PDF.")
                return FileResponse(
                    path=existing_certificate.storage_path,
                    filename=f"share_certificate_{issuance_id}.pdf",
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f"attachment; filename=share_certificate_{issuance_id}.pdf"
                    }
                )
            else:
                # Le certificat existe en base mais le fichier PDF est absent : régénérer le PDF à partir de l'issuance
                print(f"Certificate exists in DB but PDF file is missing. Regenerating PDF for issuance {issuance_id}.")
                # On récupère l'issuance pour régénérer le PDF
                issuance = await issuance_repo.find_by_id(issuance_id)
                if not issuance:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Issuance not found for certificate regeneration"
                    )
                # Générer le PDF (synchroniquement)
                pdf_generator = WeasyPrintPdfGenerator()
                regenerated_certificate = pdf_generator.generate_share_certificate(issuance)
                # Mettre à jour le storage_path du certificat existant si besoin
                existing_certificate.storage_path = regenerated_certificate.storage_path
                await certificate_repo.save(existing_certificate)
                if not os.path.exists(existing_certificate.storage_path):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Certificate file could not be regenerated"
                    )
                return FileResponse(
                    path=existing_certificate.storage_path,
                    filename=f"share_certificate_{issuance_id}.pdf",
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f"attachment; filename=share_certificate_{issuance_id}.pdf"
                    }
                )

        # Sinon, générer le certificat (cas normal)
        certificate = await certificate_service.generate_certificate_for_issuance(
            issuance_id=issuance_id,
            requesting_user_id=UUID(current_user["id"]),
            requesting_user_role=current_user["role"]
        )
        
        # Vérifier que le fichier existe
        if not os.path.exists(certificate.storage_path):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Certificate file not found after generation"
            )
        
        # Retourner le fichier PDF
        return FileResponse(
            path=certificate.storage_path,
            filename=f"share_certificate_{issuance_id}.pdf",
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=share_certificate_{issuance_id}.pdf"
            }
        )
        
    except DomainException as e:
        # Erreurs métier (accès refusé, issuance introuvable, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate file not found"
        )
    except Exception as e:
        print(f"Unexpected error generating certificate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the certificate"
        )


# Alternative: Route qui retourne les métadonnées du certificat
@router.get(
    "/{issuance_id}/certificate/info/",
    openapi_extra={"security": [{"BearerAuth": []}]}
)
async def get_certificate_info(
    issuance_id: UUID,
    current_user: dict = Depends(get_shareholder_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get certificate information without generating/downloading the file
    """
    certificate_repo = PostgresShareCertificateRepository(db)
    
    certificate = await certificate_repo.find_by_issuance_id(issuance_id)
    
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
