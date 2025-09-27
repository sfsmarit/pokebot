from dataclasses import dataclass, field
from typing import Callable

from pokebot.common.enums import Event, Stat, MoveCategory


class PokemonData:
    def __init__(self, data) -> None:
        self.name: str = data["name"]
        self.id: int = data["id"]
        self.form_id: int = data["form_id"]
        self.label: str = data["alias"]
        self.weight: float = data["weight"]
        self.types: list[str] = [data[f"type_{i+1}"] for i in range(2) if data[f"type_{i+1}"]]
        self.abilities: list[str] = [data[f"ability_{i+1}"] for i in range(3) if data[f"ability_{i+1}"]]
        self.base: list[int] = [data[s] for s in Stat.names()[:6]]


@dataclass
class AbilityData:
    flags: list[str] = field(default_factory=list)
    handlers: dict[Event, Callable] = field(default_factory=dict)
    name: str = ""


@dataclass
class ItemData:
    throw_power: int = 0
    consumable: bool = False
    handlers: dict[Event, Callable] = field(default_factory=dict)
    name: str = ""


@dataclass
class MoveData:
    type: str
    category: MoveCategory
    pp: int
    power: int = 0
    accuracy: int = 100
    priority: int = 0
    flags: list[str] = field(default_factory=list)
    handlers: dict[Event, Callable] = field(default_factory=dict)
    name: str = ""
