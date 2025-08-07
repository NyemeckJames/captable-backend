from abc import ABC, abstractmethod

class IEmailService(ABC):
    @abstractmethod
    async def send_share_issuance_notification(self, to_email: str, shareholder_name: str, quantity: int, share_class: str):
        """Simulate sending an email notification for a share issuance."""
        pass
