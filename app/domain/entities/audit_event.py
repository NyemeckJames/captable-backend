from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from uuid import UUID, uuid4

class AuditActionType(str, Enum):
    USER_LOGIN = "user_login"
    SHARE_ISSUANCE_CREATED = "share_issuance_created"

class AuditEntityType(str, Enum):
    USER = "User"
    SHARE_ISSUANCE = "ShareIssuance"

@dataclass
class AuditEvent:
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
    def create(
        cls,
        action_type: AuditActionType,
        user_id: UUID,
        target_entity_type: AuditEntityType,
        target_entity_id: UUID,
        event_metadata: Optional[Dict] = None,
        ip_address: str = "",
        user_agent: str = ""
    ) -> 'AuditEvent':
        return cls(
            id=uuid4(),
            action_type=action_type,
            user_id=user_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            event_metadata=event_metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow()
        )
