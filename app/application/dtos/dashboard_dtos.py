from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import date

from pydantic import BaseModel


@dataclass
class ShareholderSummaryDto:
    profile_id: UUID
    user_id: UUID
    name: str
    email: str
    total_shares: int
    total_value: Decimal

class ShareholderSummaryDTO(BaseModel):
    id: UUID
    name: str
    email: str
    role: str
    total_shares: int


@dataclass
class AdminDashboardDto:
    shareholders: List[ShareholderSummaryDto]
    total_issued_shares: int
    total_authorized_shares: int
    company_name: str


@dataclass
class IssuanceDto:
    id: UUID
    shareholder_profile_id: UUID
    shareholder_name: str
    share_class_id: str
    quantity: int
    price_per_share: Decimal
    total_value: Decimal
    issue_date: date

class IssuanceSummaryDTO(BaseModel):
    id: UUID
    shareholder_profile_id: UUID
    shareholder_name: str
    share_class_id: str
    quantity: int
    price_per_share: Decimal
    total_value: Decimal
    issue_date: date
