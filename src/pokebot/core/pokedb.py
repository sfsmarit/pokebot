import json

from pokebot.common import utils as ut

from pokebot.data.registry import PokemonData
from pokebot.data.ability import ABILITY
from pokebot.data.item import ITEM
from pokebot.data.move import MOVE

from .pokemon import Pokemon
from .ability import Ability
from .item import Item
from .move import Move


class PokeDB:
    zukan: dict[str, PokemonData] = {}

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
        name = name if name in ABILITY else ""
        return Ability(ABILITY[name])

    @classmethod
    def create_item(cls, name: str) -> Item:
        name = name if name in ITEM else ""
        return Item(ITEM[name])

    @classmethod
    def create_move(cls, name: str, pp: int | None = None) -> Move:
        name = name if name in MOVE else "はねる"
        return Move(MOVE[name], pp)
