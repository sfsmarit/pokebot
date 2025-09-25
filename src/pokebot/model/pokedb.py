import json

from pokebot.common import utils as ut
from .base_data import PokemonData, AbilityData, ItemData, MoveData
from .pokemon import Pokemon
from .ability import Ability
from .item import Item
from .move import Move


class PokeDB:
    pokemon: dict[str, PokemonData] = {}
    ability: dict[str, AbilityData] = {}
    item: dict[str, ItemData] = {}
    move: dict[str, MoveData] = {}

    @classmethod
    def init(cls, season: int | None = None):
        cls.season = season or ut.current_season()
        cls.load_pokemon()
        cls.load_ability()
        cls.load_item()
        cls.load_move()

    @classmethod
    def create_pokemon(cls, name: str) -> Pokemon:
        if name not in cls.pokemon:
            name = ""
        poke = Pokemon(cls.pokemon[name])
        cls.init_kata(poke)
        return poke

    @classmethod
    def create_ability(cls, name: str) -> Ability:
        if name not in cls.ability:
            name = ""
        return Ability(cls.ability[name])

    @classmethod
    def create_item(cls, name: str) -> Item:
        if name not in cls.item:
            name = ""
        return Item(cls.item[name])

    @classmethod
    def create_move(cls, name: str, pp: int | None) -> Move:
        if name not in cls.move:
            name = ""
        return Move(cls.move[name], pp)

    @classmethod
    def load_pokemon(cls):
        with open(ut.path_str('data', 'pokemon.json'), encoding='utf-8') as f:
            for _, data in json.load(f).items():
                cls.pokemon[data["name"]] = PokemonData(data)

    @classmethod
    def init_kata(cls, poke: Pokemon):
        poke.ability = cls.create_ability(cls.pokemon[poke.name].abilities[0])
        poke.item = cls.create_item("")

    @classmethod
    def load_ability(cls):
        filename = ut.path_str("data", "ability.json")
        with open(filename, encoding="utf-8") as f:
            for name, data in json.load(f).items():
                cls.ability[name] = AbilityData(name, data)

    @classmethod
    def load_item(cls):
        filename = ut.path_str("data", "item.json")
        with open(filename, encoding="utf-8") as f:
            for name, data in json.load(f).items():
                cls.item[name] = ItemData(name, data)

    @classmethod
    def load_move(cls):
        filename = ut.path_str("data", "move.json")
        with open(filename, encoding="utf-8") as f:
            for name, data in json.load(f).items():
                cls.move[name] = MoveData(name, data)
