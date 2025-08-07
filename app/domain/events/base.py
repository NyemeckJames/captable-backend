from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from typing import Dict, Any


@dataclass
class DomainEvent(ABC):
    event_id: UUID = field(init=False)
    occurred_at: datetime = field(init=False)

    def __post_init__(self):
        self.event_id = uuid4()
        self.occurred_at = datetime.now()
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass
    
    def publish(self):
        # This would be handled by the event publisher in the infrastructure layer
        # For now, we just store it in a simple registry
        EventRegistry.register(self)


class EventRegistry:
    """Simple in-memory event registry for demonstration"""
    _events = []
    
    @classmethod
    def register(cls, event: DomainEvent):
        cls._events.append(event)
    
    @classmethod
    def get_events(cls) -> list:
        return cls._events.copy()
    
    @classmethod
    def clear(cls):
        cls._events.clear()
