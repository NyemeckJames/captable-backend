import logging
import asyncio
from uuid import UUID
from app.application.commands.user_commands import CreateUserCommand
from fastapi.concurrency import run_in_threadpool
from app.application.commands.shareholder_commands import CreateShareholderCommand, CreateShareholderProfileCommand
# from app.application.commands.issuance_commands import InitiateShareIssuanceCommand
from app.application.ports.repositories import (
    ICompanyRepository,
    IUserRepository,
    IShareholderProfileRepository, 
    IShareIssuanceRepository
)
from app.application.ports.event_publisher import IEventPublisher
from app.domain.entities.user import User
from app.domain.entities.shareholder_profile import ShareholderProfile
from app.domain.value_objects.email import Email
from app.domain.value_objects.share_quantity import ShareQuantity
from app.domain.value_objects.money import Money
from app.domain.exceptions import DomainException
from app.infrastructure.api.auth.jwt_handler import get_password_hash
from app.application.ports.email_service import IEmailService

logger = logging.getLogger(__name__)


class CreateUserHandler:
    def __init__(
        self, 
        user_repository: IUserRepository,
        event_publisher: IEventPublisher
    ):
        self.user_repository = user_repository
        self.event_publisher = event_publisher
    
    async def handle(self, command: CreateUserCommand) -> UUID:
        # Check if user with this email already exists
        existing = await self.user_repository.find_by_email(command.email)
        if existing:
            raise DomainException(f"User with email {command.email} already exists")
        
        # Create new user
        user = User(
            email=Email(command.email),
            hashed_password=get_password_hash(command.password),
            role=command.role
        )
        
        # Save to repository
        saved_user = await self.user_repository.save(user)
        
        return saved_user.id


class CreateShareholderProfileHandler:
    def __init__(
        self, 
        profile_repository: IShareholderProfileRepository,
        user_repository: IUserRepository,
        event_publisher: IEventPublisher
    ):
        self.profile_repository = profile_repository
        self.user_repository = user_repository
        self.event_publisher = event_publisher
    
    async def handle(self, command: CreateShareholderProfileCommand) -> UUID:
        # Verify user exists and is a shareholder
        user = await self.user_repository.find_by_id(command.user_id)
        if not user:
            raise DomainException(f"User {command.user_id} not found")
        
        if not user.is_shareholder():
            raise DomainException("User must have shareholder role to create profile")
        
        # Check if profile already exists for this user
        existing_profile = await self.profile_repository.find_by_user_id(command.user_id)
        if existing_profile:
            raise DomainException(f"Profile already exists for user {command.user_id}")
        
        # Create new profile
        profile = ShareholderProfile.create(
            user_id=command.user_id,
            name=command.name,
            address=command.address,
            phone=command.phone
        )
        
        # Save to repository
        saved_profile = await self.profile_repository.save(profile)
        
        return saved_profile.id


class CreateShareholderHandler:
    """Combined handler to create user + profile in one transaction"""
    def __init__(
        self,
        user_repository: IUserRepository,
        profile_repository: IShareholderProfileRepository,
        event_publisher: IEventPublisher
    ):
        self.user_repository = user_repository
        self.profile_repository = profile_repository
        self.event_publisher = event_publisher
    
    async def handle(self, command: CreateShareholderCommand) -> dict:
        # Check if user with this email already exists
        existing = await self.user_repository.find_by_email(command.email)
        if existing:
            raise DomainException(f"User with email {command.email} already exists")
        
        # Create user
        user = User(
            email=Email(command.email),
            hashed_password=get_password_hash(command.password),
            role="shareholder"
        )
        saved_user = await self.user_repository.save(user)
        
        # Create profile
        profile = ShareholderProfile.create(
            user_id=saved_user.id,
            name=command.name,
            address=command.address,
            phone=command.phone
        )
        saved_profile = await self.profile_repository.save(profile)
        
        return {
            "user_id": saved_user.id,
            "profile_id": saved_profile.id
        }


class CreateIssuanceHandler:
    def __init__(
        self,
        company_repository: ICompanyRepository,
        shareholder_repository: IShareholderProfileRepository,
        issuance_repository: IShareIssuanceRepository,
        event_publisher: IEventPublisher,
        email_service: IEmailService,
    ):
        self.company_repository = company_repository
        self.shareholder_repository = shareholder_repository
        self.issuance_repository = issuance_repository
        self.event_publisher = event_publisher
        self.email_service = email_service

    async def handle(self, command) -> dict:
        """Handler avec logique métier Company intégrée"""
        
        # 1. Validation commande
        command.validate()
        
        # 2. Chargement de la Company (règles métier cruciales)
        company = await self.company_repository.find_the_company()
        if not company:
            raise DomainException("Company not found. Please initialize company first.")
        
        # 3. Validation actionnaire
        shareholder = await self.shareholder_repository.find_by_id(command.shareholder_profile_id)
        if not shareholder:
            raise DomainException(f"Shareholder profile {command.shareholder_profile_id} not found")

        # 4. Création des value objects
        quantity = ShareQuantity(command.quantity)
        price = Money(command.price_per_share, command.currency)
        
        # 5. Utilisation de la logique métier Company.issue_shares()
        # Cette méthode contient toute la validation métier (limites, classes d'actions, etc.)
        try:
            issuance = company.issue_shares(
                shareholder_profile_id=command.shareholder_profile_id,
                share_class_id=command.share_class_id,
                quantity=quantity,
                price_per_share=price,
                issue_date=command.issue_date
            )
            
        except DomainException as e:
            # Erreurs métier de la Company (ex: dépassement autorisé, classe inexistante)
            raise e
        
        # 6. Persistance de l'état modifié de la Company
        # La Company a été modifiée (issued_shares mis à jour, issuance ajoutée)
        try:
            # Sauvegarder l'état modifié de la company en premier
            await self.company_repository.save(company)
            
            # Puis sauvegarder l'issuance pour les requêtes optimisées
            saved_issuance = await self.issuance_repository.save(issuance)

            # Simulate email notification to shareholder
            if hasattr(shareholder, "email"):
                shareholder_email = getattr(shareholder, "email")
            elif hasattr(shareholder, "user") and hasattr(shareholder.user, "email"):
                shareholder_email = getattr(shareholder.user, "email")
            else:
                shareholder_email = None

            if shareholder_email:
                await self.email_service.send_share_issuance_notification(
                    to_email=shareholder_email,
                    shareholder_name=getattr(shareholder, "name", ""),
                    quantity=quantity.value,
                    share_class=command.share_class_id
                )
        except Exception as e:
            # En cas d'erreur, la transaction sera rollbackée automatiquement
            raise DomainException(f"Failed to persist issuance: {str(e)}")
        
        # Événement métier
        from app.domain.events.share_events import ShareIssuanceCompleted
        event = ShareIssuanceCompleted(
            issuance_id=saved_issuance.id,
            shareholder_profile_id=saved_issuance.shareholder_profile_id,
            quantity=saved_issuance.quantity.value,
            issue_date=saved_issuance.issue_date
        )
        await self.event_publisher.publish(event)

        return {
            "issuance_id": str(saved_issuance.id),
            "company_issued_shares": company.issued_shares.value,
            "company_authorized_shares": company.authorized_shares.value,
            "message": "Share issuance created successfully"
        }
