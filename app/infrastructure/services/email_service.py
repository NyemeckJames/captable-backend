import logging

from app.application.ports.email_service import IEmailService

logger = logging.getLogger(__name__)


class ConsoleEmailService(IEmailService):
    """Development adapter: writes the notification to the log instead of sending it.

    The recipient address is business data, not a secret, so it stays; the body is
    reduced to what identifies the event.
    """

    async def send_share_issuance_notification(
        self, to_email: str, shareholder_name: str, quantity: int, share_class: str
    ):
        logger.info(
            "Share issuance notification for %s: %s shares of class %s",
            to_email, quantity, share_class
        )
