import json

from pokebot.common import utils as ut

from pokebot.data.registry import PokemonData
from pokebot.data.ability import ABILITIES
from pokebot.data.item import ITEMS
from pokebot.data.move import MOVES

from .pokemon import Pokemon
from .ability import Ability
from .item import Item
from .move import Move


class PokeDB:
    zukan: dict[str, PokemonData] = {}
    abilities = ABILITIES
    items = ITEMS
    movess = MOVES

    @classmethod
    def init(cls, season: int | None = None):
        cls.season = season or ut.current_season()
        cls.load_zukan()

    @classmethod
    def load_zukan(cls):
        with open(ut.path_str('data', 'zukan.json'), encoding='utf-8') as f:
            for data in json.load(f).values():
                cls.zukan[data["name"]] = PokemonData(data)

    @classmethod
    def create_pokemon(cls, name: str) -> Pokemon:
        name = name if name in cls.zukan else next(iter(cls.zukan))
        poke = Pokemon(cls.zukan[name])
        cls.init_kata(poke)
        return poke

    @classmethod
    def init_kata(cls, poke: Pokemon):
        poke.ability = cls.create_ability("")
        poke.item = cls.create_item("")

    @classmethod
    def create_ability(cls, name: str) -> Ability:
        name = name if name in ABILITIES else ""
        return Ability(ABILITIES[name])

    @classmethod
    def create_item(cls, name: str) -> Item:
        name = name if name in ITEMS else ""
        return Item(ITEMS[name])

    @classmethod
    def create_move(cls, name: str, pp: int | None = None) -> Move:
        name = name if name in MOVES else "はねる"
        return Move(MOVES[name], pp)
