from enum import Enum
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from app.domain.value_objects.share_quantity import ShareQuantity
from app.domain.value_objects.money import Money
from app.domain.entities.share_issuance import ShareIssuance
from app.domain.events.share_events import ShareIssuanceCompleted
from app.domain.exceptions import DomainException
from datetime import date


class ShareType(str, Enum):
    COMMON = "common"
    PREFERRED = "preferred"

@dataclass
class ShareClass:
    id: str
    name: str
    type: ShareType = ShareType.COMMON  # "common", "preferred"
    rights: Dict[str, any] = field(default_factory=dict)


@dataclass
class OptionPool:
    total_shares: ShareQuantity
    allocated_shares: ShareQuantity = field(default_factory=lambda: ShareQuantity(0))
    
    @property
    def available_shares(self) -> ShareQuantity:
        return self.total_shares.subtract(self.allocated_shares)


@dataclass
class Company:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    authorized_shares: ShareQuantity = None
    share_classes: List[ShareClass] = field(default_factory=list)
    option_pool: Optional[OptionPool] = None
    issued_shares: ShareQuantity = field(default_factory=lambda: ShareQuantity(0))
    issuances: List[ShareIssuance] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.name:
            raise ValueError("Company name is required")
        if self.authorized_shares is None:
            raise ValueError("Authorized shares is required")
        
        # Initialize default share classes if none provided
        if not self.share_classes:
            self.share_classes = [
                ShareClass("ordinary", "Common Shares", ShareType.COMMON),
                ShareClass("preferred_a", "Series A Preferred", ShareType.PREFERRED)
            ]
    
    def authorize_new_share_class(self, class_id: str, name: str, share_type: str) -> ShareClass:
        if any(sc.id == class_id for sc in self.share_classes):
            raise DomainException(f"Share class {class_id} already exists")
        
        share_class = ShareClass(class_id, name, share_type)
        self.share_classes.append(share_class)
        return share_class
    
    def can_issue(self, quantity: ShareQuantity) -> bool:
        total_after_issuance = self.issued_shares.add(quantity)
        return total_after_issuance.value <= self.authorized_shares.value
    
    def issue_shares(
    self, 
    shareholder_profile_id: UUID, 
    share_class_id: str, 
    quantity: ShareQuantity, 
    price_per_share: Money,
    issue_date: Optional[date] = None
) -> ShareIssuance:
        # 1. Récupérer la classe d’actions ou échouer
        share_class = next((sc for sc in self.share_classes if sc.id == share_class_id), None)
        if not share_class:
            raise DomainException(f"La classe d’actions '{share_class_id}' n’existe pas.")

        # 2. Vérifier le plafond d’actions autorisées
        if not self.can_issue(quantity):
            raise DomainException(
                f"Impossible d’émettre {quantity}. Cela dépasserait le plafond d’actions autorisées ({self.authorized_shares})."
            )

        # 3. Si applicable : vérifier le pool d’options
        if share_class.type == "option" and self.option_pool:
            if quantity.value > self.option_pool.available_shares.value:
                raise DomainException("Pas assez d’actions disponibles dans le pool d’options.")
            self.option_pool.allocated_shares = self.option_pool.allocated_shares.add(quantity)

        # 4. Créer l’émission d’actions
        issuance = ShareIssuance(
            shareholder_profile_id=shareholder_profile_id,
            share_class_id=share_class_id,
            quantity=quantity,
            price_per_share=price_per_share,
            issue_date=issue_date or date.today()
        )

        # 5. Mettre à jour l’état de la compagnie
        self.issued_shares = self.issued_shares.add(quantity)
        self.issuances.append(issuance)

        # 6. Émettre un événement de domaine
        ShareIssuanceCompleted(
            issuance_id=issuance.id,
            shareholder_profile_id=shareholder_profile_id,
            quantity=quantity.value,
            issue_date=issuance.issue_date
        ).publish()

        return issuance

    def get_total_shares_for_shareholder(self, shareholder_profile_id: UUID) -> int:
        return sum(
            issuance.quantity.value 
            for issuance in self.issuances 
            if issuance.shareholder_profile_id == shareholder_profile_id
        )
