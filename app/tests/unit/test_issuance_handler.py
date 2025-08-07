import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from app.application.handlers.command_handlers import CreateIssuanceHandler
from app.application.commands.issuance_commands import CreateIssuanceCommand
from app.domain.value_objects.share_quantity import ShareQuantity
from app.domain.value_objects.money import Money

@pytest.mark.asyncio
async def test_create_issuance_business_logic():
    # Mocks
    company_repo = AsyncMock()
    shareholder_repo = AsyncMock()
    issuance_repo = AsyncMock()
    event_publisher = AsyncMock()
    email_service = AsyncMock()

    # Setup company and shareholder
    class DummyCompany:
        authorized_shares = ShareQuantity(1000000)
        issued_shares = ShareQuantity(0)
        name = "TestCo"
        def issue_shares(self, **kwargs):
            class DummyIssuance:
                id = uuid4()
                shareholder_profile_id = kwargs["shareholder_profile_id"]
                quantity = ShareQuantity(kwargs["quantity"].value)
                price_per_share = Money(kwargs["price_per_share"].amount, kwargs["price_per_share"].currency)
                share_class_id = kwargs["share_class_id"]
                issue_date = kwargs["issue_date"]
            return DummyIssuance()
    class DummyShareholder:
        id = uuid4()
        name = "Test Shareholder"
        email = "shareholder@test.com"

    dummy_company = DummyCompany()
    dummy_shareholder = DummyShareholder()
    company_repo.find_the_company.return_value = dummy_company
    shareholder_repo.find_by_id.return_value = dummy_shareholder
    company_repo.save.return_value = dummy_company
    issuance_repo.save.return_value = MagicMock(id=uuid4(), shareholder_profile_id=dummy_shareholder.id, quantity=ShareQuantity(100), price_per_share=Money(500, "XAF"), share_class_id="preferred_a", issue_date=None)

    handler = CreateIssuanceHandler(
        company_repository=company_repo,
        shareholder_repository=shareholder_repo,
        issuance_repository=issuance_repo,
        event_publisher=event_publisher,
        email_service=email_service
    )

    command = CreateIssuanceCommand(
        shareholder_profile_id=dummy_shareholder.id,
        share_class_id="preferred_a",
        quantity=100,
        price_per_share=500,
        currency="XAF",
        issue_date=None
    )

    result = await handler.handle(command)
    assert "issuance_id" in result
    email_service.send_share_issuance_notification.assert_awaited()
