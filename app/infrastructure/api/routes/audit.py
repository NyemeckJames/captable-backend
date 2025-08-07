from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.application.handlers.query_handlers import GetAuditEventsHandler
from app.application.queries.audit_queries import GetAuditEventsQuery
from app.infrastructure.api.dependencies import get_audit_service
from app.application.services.audit_service import AuditService
from app.application.dtos.audit_dtos import AuditEventDTO
from app.infrastructure.api.auth.dependencies import get_admin_user

router = APIRouter(prefix="/api/audit", tags=["Audit"])

@router.get(
    "/",
    response_model=List[AuditEventDTO],
    summary="Afficher le journal d'audit",
    description="Retourne la liste des événements d'audit (admin uniquement).",
    openapi_extra={"security": [{"BearerAuth": []}]}
)
async def get_audit_log(
    current_user: dict = Depends(get_admin_user),
    audit_service: AuditService = Depends(get_audit_service),
    limit: int = 100,
    offset: int = 0
):
    try:
        handler = GetAuditEventsHandler(GetAuditEventsQuery(audit_service))
        return await handler.handle(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du journal d'audit: {e}"
        )
