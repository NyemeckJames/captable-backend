from dataclasses import dataclass
from uuid import UUID
from app.application.commands.base import Query


@dataclass
class GetIssuanceForCertificateQuery(Query):
    issuance_id: UUID
    requesting_user_id: UUID  # Pour les contrôles d'accès
    requesting_user_role: str
