from typing import List
from app.application.ports.event_publisher import IEventPublisher
from app.domain.events.base import DomainEvent, EventRegistry


class InMemoryEventPublisher(IEventPublisher):
    """Simple in-memory event publisher for demonstration"""
    
    async def publish(self, event: DomainEvent) -> None:
        # In a real implementation, this would publish to a message queue
        # For now, we just register it in memory
        EventRegistry.register(event)
        print(f"Event published: {event.__class__.__name__} - {event.event_id}")
