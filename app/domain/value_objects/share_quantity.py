from dataclasses import dataclass
from app.domain.exceptions import DomainException


@dataclass(frozen=True)
class ShareQuantity:
    value: int
    
    def __post_init__(self):
        if self.value < 0:
            raise DomainException("Share quantity cannot be negative")
    
    def add(self, other: 'ShareQuantity') -> 'ShareQuantity':
        return ShareQuantity(self.value + other.value)
    
    def subtract(self, other: 'ShareQuantity') -> 'ShareQuantity':
        if self.value < other.value:
            raise DomainException("Cannot subtract more shares than available")
        return ShareQuantity(self.value - other.value)
    
    def __str__(self) -> str:
        return str(self.value)
