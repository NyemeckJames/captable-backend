from uuid import UUID, uuid4
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from app.domain.value_objects.money import Money
from app.domain.value_objects.share_quantity import ShareQuantity


@dataclass
class ShareIssuance:
    id: UUID = field(default_factory=uuid4)
    shareholder_profile_id: UUID = None
    shareholder_name: str = None  # Ajout du nom du détenteur
    share_class_id: str = "ordinary"
    quantity: ShareQuantity = None
    price_per_share: Money = None
    issue_date: date = field(default_factory=date.today)
    certificate_id: UUID = None
    
    def __post_init__(self):
        if self.shareholder_profile_id is None:
            raise ValueError("Shareholder profile ID is required")
        if self.quantity is None:
            raise ValueError("Share quantity is required")
        if self.price_per_share is None:
            raise ValueError("Price per share is required")
    
    @property
    def total_value(self) -> Money:
        return self.price_per_share.multiply(self.quantity.value)
