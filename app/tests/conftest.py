import asyncio
import sys

import pytest
from httpx import AsyncClient
from app.main import app
from app.infrastructure.database.connection import Base
from app.infrastructure.database.models import UserModel, ShareholderProfileModel
from app.infrastructure.database.models import CompanyModel
from app.infrastructure.api.auth.jwt_handler import get_password_hash
from sqlalchemy import select
from uuid import UUID, uuid4

if sys.platform == "win32":
    # asyncpg cannot run on the Proactor loop Windows selects by default: the
    # connection is reset mid-handshake. Without this the whole integration suite
    # is unrunnable on a Windows workstation.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def event_loop():
    """Permet d'utiliser pytest-asyncio avec scope session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

import os

@pytest.fixture(scope="session")
def test_engine():
    """Crée un moteur asynchrone pour la base de test PostgreSQL (captable_test)."""
    from sqlalchemy.ext.asyncio import create_async_engine
    # Utilise une variable d'environnement ou une valeur par défaut
    TEST_DATABASE_URL = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:root@localhost/captable_test"
    )
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    return engine

@pytest.fixture(scope="session")
async def prepare_database(test_engine):
    """Crée toutes les tables dans la base de test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Pas de drop pour SQLite in-memory, la base disparaît à la fin du process

@pytest.fixture(scope="function")
async def db_session(test_engine, prepare_database):
    """Session de base de données pour chaque test, isolée."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture(scope="function")
async def async_client(db_session):
    """Client HTTP async pour les tests, avec DB patchée."""
    # Patch la dépendance get_db pour utiliser la session de test
    from fastapi import Depends
    from app.infrastructure.database.connection import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
async def company(db_session):
    """Crée une Company pour les tests si elle n'existe pas."""
    from uuid import uuid4
    company_id = uuid4()
    company_name = "Test Company"
    # Vérifier si la company existe déjà
    result = await db_session.execute(
        select(CompanyModel).where(CompanyModel.name == company_name)
    )
    company = result.scalar_one_or_none()
    if not company:
        company = CompanyModel(
            id=company_id,
            name=company_name,
            authorized_shares=1000000,
            issued_shares=0
        )
        db_session.add(company)
        await db_session.commit()
        await db_session.refresh(company)
    return company

@pytest.fixture(scope="function")
async def admin_user(db_session, company):
    """Crée un utilisateur admin pour les tests (et une company)."""
    admin_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    admin_email = "admin@captable.com"
    admin_password = "admin123"
    admin_role = "admin"
    admin_name = "Admin User"

    # Vérifier si l'utilisateur existe déjà
    result = await db_session.execute(
        select(UserModel).where(UserModel.id == admin_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = UserModel(
            id=admin_id,
            email=admin_email,
            hashed_password=get_password_hash(admin_password),
            role=admin_role,
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

    # Vérifier si le profil existe déjà
    result = await db_session.execute(
        select(ShareholderProfileModel).where(ShareholderProfileModel.user_id == admin_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        profile = ShareholderProfileModel(
            user_id=admin_id,
            name=admin_name
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)

    # Stocker le mot de passe en clair pour les tests
    user.plain_password = admin_password
    return user

@pytest.fixture(scope="function")
async def admin_token(async_client, admin_user):
    """Génère un token JWT pour l'utilisateur admin."""
    response = await async_client.post(
        "/api/token/",
        json={
            "email": admin_user.email,
            "password": admin_user.plain_password
        }
    )
    assert response.status_code == 200, f"Authentication failed: {response.text}"
    return response.json()["access_token"]

@pytest.fixture(scope="function")
async def shareholder_user(db_session):
    """Crée un utilisateur shareholder pour les tests."""
    shareholder_id = uuid4()
    email = f"shareholder_{shareholder_id}@test.com"  # Email unique pour chaque test
    password = "shareholder123"
    role = "shareholder"
    name = "Test Shareholder"

    # Créer l'utilisateur
    user = UserModel(
        id=shareholder_id,
        email=email,
        hashed_password=get_password_hash(password),
        role=role,
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    await db_session.refresh(user)

    # Créer le profil shareholder
    profile = ShareholderProfileModel(
        user_id=user.id,
        name=name
    )
    db_session.add(profile)
    await db_session.flush()
    await db_session.commit()
    await db_session.refresh(profile)

    # Stocker le mot de passe en clair pour les tests
    user.plain_password = password
    return user, profile

@pytest.fixture(scope="function")
async def shareholder_token(async_client, shareholder_user):
    """Génère un token JWT pour l'utilisateur shareholder."""
    user, profile = shareholder_user  # Déstructuration du tuple
    response = await async_client.post(
        "/api/token/",
        json={
            "email": user.email,
            "password": user.plain_password
        }
    )
    assert response.status_code == 200, f"Authentication failed: {response.text}"
    return response.json()["access_token"]