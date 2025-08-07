from typing import List, Optional
from uuid import UUID
from app.domain.entities.audit_event import AuditEvent, AuditActionType, AuditEntityType
from app.application.ports.repositories import IAuditEventRepository

class AuditService:
    def __init__(self, audit_repository: IAuditEventRepository):
        self.audit_repository = audit_repository

    async def log_event(
        self,
        action_type: AuditActionType,
        user_id: UUID,
        target_entity_type: AuditEntityType,
        target_entity_id: UUID,
        event_metadata: Optional[dict] = None,
        ip_address: str = "",
        user_agent: str = ""
    ) -> AuditEvent:
        event = AuditEvent.create(
            action_type=action_type,
            user_id=user_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            event_metadata=event_metadata,
            ip_address=ip_address,
            user_agent=user_agent
        )
        return await self.audit_repository.save(event)

    async def get_all_events(self, limit: int = 100, offset: int = 0) -> List[AuditEvent]:
        return await self.audit_repository.find_all(limit=limit, offset=offset)

    async def get_events_by_user(self, user_id: UUID, limit: int = 100, offset: int = 0) -> List[AuditEvent]:
        return await self.audit_repository.find_by_user_id(user_id, limit=limit, offset=offset)
