from abc import ABC, abstractmethod
from app.domain.events.base import DomainEvent


class IEventPublisher(ABC):
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        pass
