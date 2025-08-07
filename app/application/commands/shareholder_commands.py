from dataclasses import dataclass
from uuid import UUID
from typing import Optional
from app.application.commands.base import Command


@dataclass
class CreateShareholderProfileCommand(Command):
    user_id: UUID
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None


@dataclass
class CreateShareholderCommand(Command):
    """Combined command to create user + profile"""
    email: str
    password: str
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
