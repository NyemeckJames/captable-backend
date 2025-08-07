from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.infrastructure.api.auth.dependencies import get_admin_user
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.repositories.shareholder_repository import PostgresShareholderRepository
from app.infrastructure.database.repositories.company_repository import PostgresCompanyRepository
from app.infrastructure.database.repositories.issuance_repository import PostgresShareIssuanceRepository
from app.infrastructure.services.event_service import InMemoryEventPublisher
from app.application.commands.shareholder_commands import CreateShareholderCommand
from app.application.queries.dashboard_queries import GetAdminDashboardQuery, GetAllShareholdersQuery
from app.application.handlers.command_handlers import CreateShareholderHandler
from app.application.handlers.query_handlers import GetAdminDashboardHandler, GetAllShareholdersHandler
from app.application.dtos.dashboard_dtos import AdminDashboardDto, ShareholderSummaryDTO
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/shareholders", tags=["Shareholders"])


class CreateShareholderRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    address: str = None
    phone: str = None
    role: str = "shareholder"


class ShareholderResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: str


@router.get(
    "/",
    response_model=AdminDashboardDto,
    summary="Liste des actionnaires et parts (Admin)",
    description="Liste tous les actionnaires avec leurs parts et informations de dashboard. Réservé aux administrateurs.",
    tags=["Shareholders"],
    responses={
        200: {
            "description": "Dashboard des actionnaires retourné avec succès",
            "content": {
                "application/json": {
                    "example": {
                        "total_shareholders": 2,
                        "total_shares": 1000,
                        "shareholders": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "name": "Alice Dupont",
                                "email": "alice@captable.com",
                                "role": "shareholder",
                                "shares": 500
                            },
                            {
                                "id": "660e8400-e29b-41d4-a716-446655440000",
                                "name": "Bob Martin",
                                "email": "bob@captable.com",
                                "role": "shareholder",
                                "shares": 500
                            }
                        ]
                    }
                }
            }
        },
        401: {"description": "Non autorisé (admin requis)"},
        422: {"description": "Erreur de validation des données"}
    },
    openapi_extra={"security": [{"BearerAuth": []}]}
)
async def get_shareholders_dashboard(
    current_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Liste tous les actionnaires avec leurs parts et informations de dashboard. Réservé aux administrateurs."""
    shareholder_repo = PostgresShareholderRepository(db)
    company_repo = PostgresCompanyRepository(db)
    issuance_repo = PostgresShareIssuanceRepository(db)
    
    handler = GetAdminDashboardHandler(shareholder_repo, company_repo, issuance_repo)
    query = GetAdminDashboardQuery()
    
    result = await handler.handle(query)
    return result


@router.post(
    "/",
    response_model=dict,
    summary="Créer un actionnaire (Admin)",
    description="Crée un nouvel actionnaire. Réservé aux administrateurs.",
    tags=["Shareholders"],
    responses={
        200: {
            "description": "Actionnaire créé avec succès",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "profile_id": "660e8400-e29b-41d4-a716-446655440000",
                        "message": "Shareholder created successfully"
                    }
                }
            }
        },
        400: {"description": "Erreur de création (email déjà utilisé, etc.)"},
        401: {"description": "Non autorisé (admin requis)"},
        422: {"description": "Erreur de validation des données"}
    },
    openapi_extra={"security": [{"BearerAuth": []}]}
)
async def create_shareholder(
    request: CreateShareholderRequest,
    current_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Crée un nouvel actionnaire. Réservé aux administrateurs.

    Exemple de requête :
    {
        "name": "Alice Dupont",
        "email": "alice@captable.com",
        "password": "alice123",
        "address": "123 rue de Paris",
        "phone": "+33612345678",
        "role": "shareholder"
    }
    """
    from app.infrastructure.database.repositories.user_repository import PostgresUserRepository
    from app.infrastructure.database.repositories.shareholder_profile_repository import PostgresShareholderProfileRepository

    user_repo = PostgresUserRepository(db)
    profile_repo = PostgresShareholderProfileRepository(db)
    event_publisher = InMemoryEventPublisher()

    handler = CreateShareholderHandler(user_repo, profile_repo, event_publisher)
    command = CreateShareholderCommand(
        email=request.email,
        password=request.password,
        name=request.name,
        address=request.address,
        phone=request.phone
    )

    try:
        result = await handler.handle(command)
        return {
            "user_id": str(result["user_id"]),
            "profile_id": str(result["profile_id"]),
            "message": "Shareholder created successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get(
    "/list",
    response_model=List[ShareholderSummaryDTO],
    openapi_extra={"security": [{"BearerAuth": []}]}
)
async def list_shareholders(
    current_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all shareholders and their total shares (admin only)"""
    shareholder_repo = PostgresShareholderRepository(db)
    handler = GetAllShareholdersHandler(shareholder_repo)
    query = GetAllShareholdersQuery()
    result = await handler.handle(query)
    return result
