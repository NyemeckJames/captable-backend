from dataclasses import dataclass
from uuid import UUID
from decimal import Decimal
from datetime import date
from app.application.commands.base import Command


@dataclass
class CreateIssuanceCommand(Command):
    shareholder_profile_id: UUID
    share_class_id: str
    quantity: int
    price_per_share: Decimal
    currency: str = "EUR"
    issue_date: date = None

    def validate(self):
        if not self.shareholder_profile_id:
            raise ValueError("Shareholder profile ID is required")
        if not self.share_class_id:
            raise ValueError("Share class ID is required")
        if self.quantity is None or self.quantity <= 0:
            raise ValueError("Quantity must be a positive integer")
        if self.price_per_share is None or self.price_per_share <= 0:
            raise ValueError("Price per share must be a positive number")
