from dataclasses import dataclass
from uuid import UUID
from datetime import date
from typing import Dict, Any
from .base import DomainEvent


@dataclass
class ShareholderCreated(DomainEvent):
    shareholder_id: UUID
    name: str
    email: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": "ShareholderCreated",
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "shareholder_id": str(self.shareholder_id),
            "name": self.name,
            "email": str(self.email)
        }

@dataclass
class ShareholderProfileCreated(DomainEvent):
    profile_id: UUID
    user_id: UUID
    name: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": "ShareholderProfileCreated",
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "profile_id": str(self.profile_id),
            "user_id": str(self.user_id),
            "name": self.name
        }


@dataclass
class ShareIssuanceCompleted(DomainEvent):
    issuance_id: UUID
    shareholder_profile_id: UUID
    quantity: int
    issue_date: date
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": "ShareIssuanceCompleted",
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "issuance_id": str(self.issuance_id),
            "shareholder_profile_id": str(self.shareholder_profile_id),
            "quantity": self.quantity,
            "issue_date": self.issue_date.isoformat()
        }


@dataclass
class CertificateGenerated(DomainEvent):
    certificate_id: UUID
    issuance_id: UUID
    storage_path: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": "CertificateGenerated",
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "certificate_id": str(self.certificate_id),
            "issuance_id": str(self.issuance_id),
            "storage_path": self.storage_path
        }
