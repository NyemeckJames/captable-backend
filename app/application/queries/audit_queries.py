from typing import List
from app.application.services.audit_service import AuditService
from app.application.dtos.audit_dtos import AuditEventDTO

class GetAuditEventsQuery:
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    async def execute(self, limit: int = 100, offset: int = 0) -> List[AuditEventDTO]:
        events = await self.audit_service.get_all_events(limit=limit, offset=offset)
        return [AuditEventDTO.from_entity(event) for event in events]
