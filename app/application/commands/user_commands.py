from dataclasses import dataclass
from app.application.commands.base import Command


@dataclass
class CreateUserCommand(Command):
    email: str
    password: str
    role: str = "shareholder"
