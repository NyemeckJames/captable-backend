from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.infrastructure.database.connection import async_engine
from app.infrastructure.database.models import Base
from app.infrastructure.api.routes import auth, shareholders, issuances
from app.infrastructure.api.routes import audit as audit_routes
from app.infrastructure.database.repositories.audit_repository import AuditEventRepository
from app.application.services.audit_service import AuditService
from app.infrastructure.database.connection import AsyncSessionLocal
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.config.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Creating database tables...")
    async with async_engine.begin() as conn:
        # await conn.run_sync(Base.metadata.create_all)  # Désactivé : utiliser Alembic pour la gestion du schéma
        pass

    # Initialize default company and test data
    await initialize_default_data()

    yield

    # Shutdown
    await async_engine.dispose()


app = FastAPI(
    title="Cap Table Management API",
    description="Backend API for managing company capitalization tables",
    version="1.0.0",
    lifespan=lifespan
)

# Ajout du schéma de sécurité JWT Bearer à la documentation OpenAPI
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Authorization header using the Bearer scheme. Example: 'Authorization: Bearer {token}'"
        }
    }
    # Déclare uniquement le schéma de sécurité, sans l'appliquer globalement
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency for AuditService
async def get_audit_service(db: AsyncSession = Depends(AsyncSessionLocal)):
    repo = AuditEventRepository(db)
    return AuditService(repo)

# Include routers
app.include_router(auth.router)
app.include_router(shareholders.router)
app.include_router(issuances.router)
app.include_router(audit_routes.router)


@app.get("/")
async def root():
    return {"message": "Cap Table Management API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


async def initialize_default_data():
    """Initialize default company and test shareholders"""
    from app.infrastructure.database.connection import AsyncSessionLocal
    from app.infrastructure.database.repositories.company_repository import PostgresCompanyRepository
    from app.infrastructure.database.repositories.shareholder_repository import PostgresShareholderRepository
    from app.domain.entities.company import Company
    from app.domain.entities.shareholder import Shareholder
    from app.domain.value_objects.share_quantity import ShareQuantity
    from app.domain.value_objects.email import Email
    from uuid import UUID
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        company_repo = PostgresCompanyRepository(session)
        shareholder_repo = PostgresShareholderRepository(session)

        from app.infrastructure.database.models import UserModel, ShareholderProfileModel
        from app.infrastructure.api.auth.jwt_handler import get_password_hash

        # Check if company already exists
        existing_company = await company_repo.find_the_company()
        if not existing_company:
            # Create default company
            company = Company(
                name=settings.company_name,
                authorized_shares=ShareQuantity(int(settings.company_authorized_shares)),
            )
            await company_repo.save(company)
            print(f"Created default company: {settings.company_name}")

        # Check if test user exists

        admin_user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        admin_email = settings.admin_email
        admin_name = settings.admin_name
        admin_role = settings.admin_role
        admin_password = settings.admin_password

        user = await session.execute(
            select(UserModel).where(UserModel.id == admin_user_id)
        )
        db_user = user.scalar_one_or_none()
        if not db_user:
            db_user = UserModel(
                id=admin_user_id,
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                role=admin_role,
                is_active=True
            )
            session.add(db_user)
            await session.commit()
            await session.refresh(db_user)

        # Ne créer un profil shareholder que si ce n'est PAS un admin
        if db_user.role != "admin":
            profile = await session.execute(
                select(ShareholderProfileModel).where(ShareholderProfileModel.user_id == admin_user_id)
            )
            db_profile = profile.scalar_one_or_none()
            if not db_profile:
                db_profile = ShareholderProfileModel(
                    user_id=admin_user_id,
                    name=admin_name
                )
                session.add(db_profile)
                await session.commit()
                await session.refresh(db_profile)
                print(f"Created shareholder profile: {admin_name}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
