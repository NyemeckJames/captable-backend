from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from app.domain.entities.company import Company
from app.domain.entities.user import User
from app.domain.entities.shareholder_profile import ShareholderProfile
from app.domain.entities.share_issuance import ShareIssuance
from app.domain.entities.share_certificate import ShareCertificate
from app.domain.entities.shareholder import Shareholder
from app.domain.entities.audit_event import AuditEvent
from typing import Any

class IUserRepository(ABC):
    @abstractmethod
    async def save(self, user: User) -> User:
        pass
    
    @abstractmethod
    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        pass
    
    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        pass
    
    @abstractmethod
    async def find_all(self) -> List[User]:
        pass


class IShareholderProfileRepository(ABC):
    @abstractmethod
    async def save(self, profile: ShareholderProfile) -> ShareholderProfile:
        pass
    
    @abstractmethod
    async def find_by_id(self, profile_id: UUID) -> Optional[ShareholderProfile]:
        pass
    
    @abstractmethod
    async def find_by_user_id(self, user_id: UUID) -> Optional[ShareholderProfile]:
        pass
    
    @abstractmethod
    async def find_all(self) -> List[ShareholderProfile]:
        pass


class ICompanyRepository(ABC):
    @abstractmethod
    async def save(self, company: Company) -> Company:
        pass
    
    @abstractmethod
    async def find_the_company(self) -> Optional[Company]:
        pass


class IShareIssuanceRepository(ABC):
    @abstractmethod
    async def save(self, issuance: ShareIssuance) -> ShareIssuance:
        """
        Sauvegarde une issuance (création ou mise à jour)
        
        Args:
            issuance: L'issuance à sauvegarder
            
        Returns:
            L'issuance sauvegardée avec les données mises à jour
        """
        pass
    
    @abstractmethod
    async def find_by_id(self, issuance_id: UUID) -> Optional[ShareIssuance]:
        """
        Trouve une issuance par son ID
        
        Args:
            issuance_id: L'UUID de l'issuance
            
        Returns:
            L'issuance si trouvée, None sinon
        """
        pass
    
    @abstractmethod
    async def find_by_shareholder_profile_id(self, profile_id: UUID) -> List[ShareIssuance]:
        """
        Trouve toutes les issuances d'un profil shareholder
        
        Args:
            profile_id: L'UUID du profil shareholder
            
        Returns:
            Liste des issuances pour ce profil (peut être vide)
        """
        pass
    
    @abstractmethod
    async def find_all(self) -> List[ShareIssuance]:
        """
        Trouve toutes les issuances
        
        Returns:
            Liste de toutes les issuances (peut être vide)
        """
        pass


class IShareholderRepository(ABC):
    @abstractmethod
    async def save(self, shareholder: Shareholder) -> Shareholder:
        pass

    @abstractmethod
    async def find_by_id(self, shareholder_id: UUID) -> Optional[Shareholder]:
        pass

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[Shareholder]:
        pass

    @abstractmethod
    async def find_all(self) -> List[Shareholder]:
        pass


class IShareCertificateRepository(ABC):
    @abstractmethod
    async def save(self, certificate: ShareCertificate) -> ShareCertificate:
        pass
    
    @abstractmethod
    async def find_by_issuance_id(self, issuance_id: UUID) -> Optional[ShareCertificate]:
        pass

class IAuditEventRepository(ABC):
    @abstractmethod
    async def save(self, event: AuditEvent) -> AuditEvent:
        pass

    @abstractmethod
    async def find_all(self, limit: int = 100, offset: int = 0) -> list[AuditEvent]:
        pass

    @abstractmethod
    async def find_by_user_id(self, user_id: UUID, limit: int = 100, offset: int = 0) -> list[AuditEvent]:
        pass
