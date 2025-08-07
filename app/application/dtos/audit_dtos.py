from uuid import UUID
from datetime import datetime
from typing import Dict
from pydantic import BaseModel
from app.domain.entities.audit_event import AuditActionType, AuditEntityType

class AuditEventDTO(BaseModel):
    id: UUID
    action_type: AuditActionType
    user_id: UUID
    target_entity_type: AuditEntityType
    target_entity_id: UUID
    event_metadata: Dict
    ip_address: str
    user_agent: str
    timestamp: datetime

    @classmethod
    def from_entity(cls, event):
        return cls(
            id=event.id,
            action_type=event.action_type,
            user_id=event.user_id,
            target_entity_type=event.target_entity_type,
            target_entity_id=event.target_entity_id,
            event_metadata=event.event_metadata,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            timestamp=event.timestamp
        )
