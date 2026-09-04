"""Create the bootstrap company and admin account.

Deliberately a script and not an application startup hook: creating a privileged
account is an administrative act that must be run knowingly, once, against a
chosen database, and must leave a trace in whoever ran it. Booting the API must
never mint credentials.

Usage:
    python -m scripts.seed_admin
"""
import asyncio
import logging

from sqlalchemy import select

from app.domain.entities.company import Company
from app.domain.value_objects.share_quantity import ShareQuantity
from app.infrastructure.api.auth.jwt_handler import get_password_hash
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.connection import AsyncSessionLocal
from app.infrastructure.database.models import ShareholderProfileModel, UserModel
from app.infrastructure.database.repositories.company_repository import PostgresCompanyRepository

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed_admin")

settings = get_settings()


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        company_repo = PostgresCompanyRepository(session)

        if not await company_repo.find_the_company():
            await company_repo.save(
                Company(
                    name=settings.company_name,
                    authorized_shares=ShareQuantity(int(settings.company_authorized_shares)),
                )
            )
            logger.info("Created company %s", settings.company_name)
        else:
            logger.info("Company already present, left untouched")

        result = await session.execute(
            select(UserModel).where(UserModel.email == settings.admin_email)
        )
        user = result.scalar_one_or_none()

        if user:
            logger.info("Admin %s already exists, password left untouched", settings.admin_email)
            return

        user = UserModel(
            email=settings.admin_email,
            hashed_password=get_password_hash(settings.admin_password),
            role=settings.admin_role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("Created admin %s", settings.admin_email)

        if user.role != "admin":
            session.add(ShareholderProfileModel(user_id=user.id, name=settings.admin_name))
            await session.commit()
            logger.info("Created shareholder profile for %s", settings.admin_email)


if __name__ == "__main__":
    asyncio.run(seed())
