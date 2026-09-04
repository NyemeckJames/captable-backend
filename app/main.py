import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.infrastructure.api.routes import audit as audit_routes
from app.infrastructure.api.routes import auth, issuances, shareholders
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.connection import async_engine

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The schema is owned by Alembic. Seeding is a deliberate administrative act,
    # not a side effect of starting the application: see scripts/seed_admin.py.
    logger.info("Starting Cap Table API in %s mode", settings.environment)
    yield
    await async_engine.dispose()


# Interactive documentation is part of the exposed surface: it stays closed in
# production and open everywhere else.
_docs_enabled = not settings.is_production

app = FastAPI(
    title="Cap Table Management API",
    description="Backend API for managing company capitalization tables",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None
)


def custom_openapi():
    """Declare the JWT bearer scheme without applying it globally.

    Routes opt in through `openapi_extra`, so an unauthenticated endpoint is
    never documented as if it were protected.
    """
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
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
