from uuid import UUID, uuid4
from dataclasses import dataclass, field
from app.domain.value_objects.email import Email


@dataclass
class User:
    id: UUID = field(default_factory=uuid4)
    email: Email = None
    hashed_password: str = ""
    role: str = "shareholder"  # "admin", "shareholder"
    is_active: bool = True
    
    def __post_init__(self):
        if self.email is None:
            raise ValueError("User email is required")
        if not self.hashed_password:
            raise ValueError("User password is required")
        if self.role not in ["admin", "shareholder"]:
            raise ValueError("Invalid user role")
    
    def is_admin(self) -> bool:
        return self.role == "admin"
    
    def is_shareholder(self) -> bool:
        return self.role == "shareholder"
