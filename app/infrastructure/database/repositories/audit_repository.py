from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from app.domain.entities.audit_event import AuditEvent, AuditActionType, AuditEntityType
from app.application.ports.repositories import IAuditEventRepository
from app.infrastructure.database.models import AuditEventModel
import json

class AuditEventRepository(IAuditEventRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, event: AuditEvent) -> AuditEvent:
        db_event = AuditEventModel(
            id=event.id,
            action_type=event.action_type.value,
            user_id=event.user_id,
            target_entity_type=event.target_entity_type.value,
            target_entity_id=event.target_entity_id,
            event_metadata=json.dumps(event.event_metadata),
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            timestamp=event.timestamp
        )
        self.session.add(db_event)
        await self.session.commit()
        await self.session.refresh(db_event)
        return event

    async def find_all(self, limit: int = 100, offset: int = 0) -> List[AuditEvent]:
        result = await self.session.execute(
            select(AuditEventModel).order_by(desc(AuditEventModel.timestamp)).limit(limit).offset(offset)
        )
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]

    async def find_by_user_id(self, user_id: UUID, limit: int = 100, offset: int = 0) -> List[AuditEvent]:
        result = await self.session.execute(
            select(AuditEventModel)
            .where(AuditEventModel.user_id == user_id)
            .order_by(desc(AuditEventModel.timestamp))
            .limit(limit)
            .offset(offset)
        )
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]

    def _to_entity(self, row: AuditEventModel) -> AuditEvent:
        return AuditEvent(
            id=row.id,
            action_type=AuditActionType(row.action_type),
            user_id=row.user_id,
            target_entity_type=AuditEntityType(row.target_entity_type),
            target_entity_id=row.target_entity_id,
            event_metadata=json.loads(row.event_metadata) if row.event_metadata else {},
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            timestamp=row.timestamp
        )
