"""Unit tests for the certificate scope check.

These pin the rule itself, independently of any route: a shareholder reaches an
issuance only through the profile that belongs to them.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.application.services.certificate_service import CertificateGenerationService
from app.domain.exceptions import AccessDeniedException, DomainException


def _service(issuance=None, profile=None):
    issuance_repo = AsyncMock()
    issuance_repo.find_by_id.return_value = issuance

    profile_repo = AsyncMock()
    profile_repo.find_by_id.return_value = profile

    return CertificateGenerationService(
        issuance_repository=issuance_repo,
        profile_repository=profile_repo,
        user_repository=AsyncMock(),
        certificate_repository=AsyncMock(),
        pdf_generator=MagicMock(),
        event_publisher=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_owner_is_authorized():
    owner_id = uuid4()
    issuance = MagicMock(shareholder_profile_id=uuid4())
    profile = MagicMock(user_id=owner_id)

    service = _service(issuance, profile)

    assert await service.authorize_issuance_access(uuid4(), owner_id, "shareholder") is issuance


@pytest.mark.asyncio
async def test_foreign_shareholder_is_denied():
    issuance = MagicMock(shareholder_profile_id=uuid4())
    profile = MagicMock(user_id=uuid4())  # belongs to somebody else

    service = _service(issuance, profile)

    with pytest.raises(AccessDeniedException):
        await service.authorize_issuance_access(uuid4(), uuid4(), "shareholder")


@pytest.mark.asyncio
async def test_admin_is_authorized_without_profile_lookup():
    issuance = MagicMock(shareholder_profile_id=uuid4())
    service = _service(issuance, profile=None)

    assert await service.authorize_issuance_access(uuid4(), uuid4(), "admin") is issuance
    service.profile_repository.find_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_issuance_is_not_reported_as_denied():
    """A missing issuance is a 404, not a 403: the two must not be confused."""
    service = _service(issuance=None)

    with pytest.raises(DomainException) as exc_info:
        await service.authorize_issuance_access(uuid4(), uuid4(), "shareholder")

    assert not isinstance(exc_info.value, AccessDeniedException)
