import logging

from app.application.ports.event_publisher import IEventPublisher
from app.domain.events.base import DomainEvent, EventRegistry

logger = logging.getLogger(__name__)


class InMemoryEventPublisher(IEventPublisher):
    """In-process publisher standing in for a broker.

    The port is what matters here: replacing this adapter with a real queue
    changes no caller.
    """

    async def publish(self, event: DomainEvent) -> None:
        EventRegistry.register(event)
        logger.debug("Event published: %s %s", event.__class__.__name__, event.event_id)
