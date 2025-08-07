from uuid import UUID, uuid4
from dataclasses import dataclass, field
from typing import Optional
from app.domain.events.share_events import ShareholderProfileCreated


@dataclass
class ShareholderProfile:
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = None
    name: str = ""
    address: Optional[str] = None
    phone: Optional[str] = None
    
    def __post_init__(self):
        if self.user_id is None:
            raise ValueError("User ID is required")
        if not self.name:
            raise ValueError("Shareholder name is required")
    
    def update_info(self, name: str, address: Optional[str] = None, phone: Optional[str] = None) -> None:
        self.name = name
        self.address = address
        self.phone = phone
    
    @classmethod
    def create(cls, user_id: UUID, name: str, address: Optional[str] = None, phone: Optional[str] = None) -> 'ShareholderProfile':
        profile = cls(
            user_id=user_id,
            name=name,
            address=address,
            phone=phone
        )
        # Emit domain event
        ShareholderProfileCreated(profile.id, user_id, name).publish()
        return profile
