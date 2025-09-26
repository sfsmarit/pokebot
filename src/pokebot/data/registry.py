from dataclasses import dataclass
from typing import Callable

from pokebot.common.enums import Trigger, MoveCategory


@dataclass
class PokemonData:
    name: str
    id: int
    form_id: int
    label: str
    weight: float
    types: list[str]
    abilities: list[str]
    base: list[int]


@dataclass
class AbilityData:
    name: str
    flags: list[str] = []


@dataclass
class ItemData:
    name: str
    throw_power: int = 0
    consumable: bool = False


@dataclass
class MoveData:
    type: str
    category: MoveCategory
    pp: int
    power: int = 0
    accuracy: int = 100
    priority: int = 0
    flags: list[str] = []
    handlers: dict[Trigger, Callable] = {}
