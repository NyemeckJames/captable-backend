from app.application.ports.email_service import IEmailService

class ConsoleEmailService(IEmailService):
    async def send_share_issuance_notification(self, to_email: str, shareholder_name: str, quantity: int, share_class: str):
        print(f"[EMAIL SIMULATION] Notification envoyée à {to_email} ({shareholder_name}) :")
        print(f"  Félicitations ! {quantity} actions de la classe '{share_class}' ont été émises à votre nom.")
