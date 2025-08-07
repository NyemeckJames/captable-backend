from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from app.domain.exceptions import DomainException


class BaseRepository:
    """Base repository avec gestion des erreurs async"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def _execute_query(self, query_func, *args, **kwargs):
        """
        Wrapper pour exécuter les requêtes avec gestion d'erreurs
        """
        try:
            return await query_func(*args, **kwargs)
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DomainException(f"Database error: {str(e)}")
        except Exception as e:
            await self.session.rollback()
            raise DomainException(f"Unexpected repository error: {str(e)}")
