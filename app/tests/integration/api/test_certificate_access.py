"""Scope regression tests for share certificates.

The vulnerability these cover: the download route used to short-circuit on an
already generated certificate and return the PDF without ever calling the service
that checks ownership. Any authenticated shareholder could therefore read another
shareholder's certificate by changing the UUID in the URL, from the second request
onwards. The metadata route performed no ownership check at all.

Both tests deliberately create the certificate row first, because that is the state
in which the bypass existed.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4

from app.infrastructure.api.auth.jwt_handler import get_password_hash
from app.infrastructure.database.models import (
    ShareCertificateModel,
    ShareholderProfileModel,
    UserModel,
)


async def _make_shareholder(db_session: AsyncSession, async_client: AsyncClient):
    """Create a second shareholder and return (user, profile, bearer token)."""
    password = "outsider123"
    user = UserModel(
        id=uuid4(),
        email=f"outsider_{uuid4()}@test.com",
        hashed_password=get_password_hash(password),
        role="shareholder",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = ShareholderProfileModel(user_id=user.id, name="Outsider")
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    response = await async_client.post(
        "/api/token/", json={"email": user.email, "password": password}
    )
    assert response.status_code == 200, f"Authentication failed: {response.text}"
    return user, profile, response.json()["access_token"]


async def _issuance_with_certificate(
    async_client: AsyncClient, db_session: AsyncSession, admin_token: str, profile_id, tmp_path
):
    """Issue shares to `profile_id` and attach a certificate file to the issuance."""
    response = await async_client.post(
        "/api/issuances/",
        json={
            "shareholder_id": str(profile_id),
            "share_class_id": "preferred_a",
            "quantity": 100,
            "price_per_share": 500,
            "currency": "XAF",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, f"Issuance creation failed: {response.text}"
    issuance_id = response.json()["issuance_id"]

    pdf_path = tmp_path / f"certificate_{issuance_id}.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test certificate")

    db_session.add(
        ShareCertificateModel(
            id=uuid4(),
            share_issuance_id=UUID(issuance_id),
            watermark="TEST",
            storage_path=str(pdf_path),
        )
    )
    await db_session.commit()

    return issuance_id


@pytest.mark.asyncio
async def test_foreign_shareholder_cannot_download_certificate(
    async_client: AsyncClient, db_session: AsyncSession, admin_token: str, shareholder_user, tmp_path
):
    _, owner_profile = shareholder_user
    issuance_id = await _issuance_with_certificate(
        async_client, db_session, admin_token, owner_profile.id, tmp_path
    )
    _, _, outsider_token = await _make_shareholder(db_session, async_client)

    response = await async_client.get(
        f"/api/issuances/{issuance_id}/certificate/",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )

    assert response.status_code == 403, (
        f"A foreign shareholder must not reach another certificate, got "
        f"{response.status_code}: {response.text[:200]}"
    )


@pytest.mark.asyncio
async def test_foreign_shareholder_cannot_read_certificate_metadata(
    async_client: AsyncClient, db_session: AsyncSession, admin_token: str, shareholder_user, tmp_path
):
    _, owner_profile = shareholder_user
    issuance_id = await _issuance_with_certificate(
        async_client, db_session, admin_token, owner_profile.id, tmp_path
    )
    _, _, outsider_token = await _make_shareholder(db_session, async_client)

    response = await async_client.get(
        f"/api/issuances/{issuance_id}/certificate/info/",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )

    assert response.status_code == 403, (
        f"Certificate metadata must follow the same perimeter as the file, got "
        f"{response.status_code}: {response.text[:200]}"
    )


@pytest.mark.asyncio
async def test_owner_reads_own_certificate_metadata(
    async_client: AsyncClient, db_session: AsyncSession, admin_token: str, shareholder_user, tmp_path
):
    """The lock must not close on the legitimate holder."""
    owner_user, owner_profile = shareholder_user
    issuance_id = await _issuance_with_certificate(
        async_client, db_session, admin_token, owner_profile.id, tmp_path
    )

    response = await async_client.post(
        "/api/token/",
        json={"email": owner_user.email, "password": owner_user.plain_password},
    )
    assert response.status_code == 200, f"Authentication failed: {response.text}"
    owner_token = response.json()["access_token"]

    response = await async_client.get(
        f"/api/issuances/{issuance_id}/certificate/info/",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200, (
        f"The certificate holder must keep access, got "
        f"{response.status_code}: {response.text[:200]}"
    )
    assert response.json()["issuance_id"] == issuance_id
