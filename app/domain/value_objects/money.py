from dataclasses import dataclass
from decimal import Decimal
from app.domain.exceptions import DomainException


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "EUR"
    
    def __post_init__(self):
        if self.amount < 0:
            raise DomainException("Money amount cannot be negative")
        if not self.currency or len(self.currency) != 3:
            raise DomainException("Currency must be a 3-letter code")
    
    def multiply(self, factor: int) -> 'Money':
        return Money(self.amount * factor, self.currency)
    
    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"
