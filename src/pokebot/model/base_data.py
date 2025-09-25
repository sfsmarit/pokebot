from pokebot.common.constants import STAT_CODES
from pokebot.common.enums import MoveCategory


class PokemonData:
    def __init__(self, data: dict) -> None:
        self.name: str = data["name"]
        self.id: int = data["id"]
        self.form_id: int = data["form_id"]
        self.label: str = data["alias"]
        self.weight: float = data["weight"]
        self.types: list[str] = [data[f"type_{i+1}"] for i in range(2) if data[f"type_{i+1}"]]
        self.abilities: list[str] = [data[f"ability_{i+1}"] for i in range(3) if data[f"ability_{i+1}"]]
        self.base: list[int] = [data[c] for c in STAT_CODES[:6]]


class AbilityData:
    def __init__(self, name: str, data: dict) -> None:
        self.name: str = name
        self.flags: list[str] = data.get("flags", [])
        self.effects: list[dict] = data.get("effects", [])


class ItemData:
    def __init__(self, name: str, data: dict) -> None:
        self.name: str = name
        self.consumable: bool = data["consumable"]
        self.throw_power: int = data["throw_power"]
        self.effects: list[dict] = data.get("effects", [])


class MoveData:
    def __init__(self, name: str, data: dict) -> None:
        self.name: str = name
        self.type: str = data["type"]
        self.category: MoveCategory = MoveCategory(data["category"])
        self.pp: int = data["pp"]
        self.power: int = data.get("power", 0)
        self.accuracy: int = data.get("accuracy", 100)
        self.priority: int = data.get("priority", 0)
        self.flags: list[str] = data.get("flags", [])
        self.effects: list[dict] = data.get("effects", [])
