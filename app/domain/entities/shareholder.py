from uuid import UUID, uuid4
from dataclasses import dataclass, field
from app.domain.value_objects.email import Email
from app.domain.events.share_events import ShareholderCreated


@dataclass
class Shareholder:
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = None
    name: str = ""
    email: Email = None
    role: str = "shareholder"  # "founder", "investor", "employee", "shareholder"
    
    def __post_init__(self):
        if not self.name:
            raise ValueError("Shareholder name is required")
        if self.email is None:
            raise ValueError("Shareholder email is required")
    
    def update_contact_info(self, name: str, email: str) -> None:
        self.name = name
        self.email = Email(email)
    
    @classmethod
    def create(cls, name: str, email: str, role: str = "shareholder") -> 'Shareholder':
        shareholder = cls(
            name=name,
            email=Email(email),
            role=role
        )
        # Emit domain event
        ShareholderCreated(shareholder.id, name, email).publish()
        return shareholder
