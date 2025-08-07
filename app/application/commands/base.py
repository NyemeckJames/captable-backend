from abc import ABC
from dataclasses import dataclass


@dataclass
class Command(ABC):
    pass


@dataclass
class Query(ABC):
    pass
