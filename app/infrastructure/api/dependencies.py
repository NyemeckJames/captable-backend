from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.repositories.audit_repository import AuditEventRepository
from app.application.services.audit_service import AuditService

def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    repo = AuditEventRepository(db)
    return AuditService(repo)
