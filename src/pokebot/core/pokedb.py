import json
from datetime import datetime, timedelta, timezone

from pokebot import config
from pokebot.utils.enums import Gender
from pokebot.utils import file_utils as fileut

from pokebot.data import ABILITIES, ITEMS, MOVES
from pokebot.data.registry import PokemonData

from pokebot.model import Pokemon, Ability, Item, Move


def get_season(start_year=2022, start_month=12) -> int:
    dt_now = datetime.now(timezone(timedelta(hours=+9), 'JST'))
    y, m, d = dt_now.year, dt_now.month, dt_now.day
    season = 12*(y-start_year) + m - start_month + 1 - (d == 1)
    return max(season, 1)


class PokeDB:
    zukan: dict[str, PokemonData] = {}
    abilities = ABILITIES
    items = ITEMS
    movess = MOVES

    @classmethod
    def init(cls, season: int | None = None):
        cls.season = season or get_season()
        cls.load_zukan()

    @classmethod
    def load_zukan(cls):
        file = str(fileut.resource_path('data', "zukan.json"))

        if fileut.needs_update(file):
            fileut.download(config.URL_ZUKAN, file)
            fileut.save_last_update(file)

        with open(file, encoding='utf-8') as f:
            zukan = json.load(f)
            for data in zukan.values():
                cls.zukan[data["name"]] = PokemonData(data)

    @classmethod
    def create_pokemon(cls, name: str) -> Pokemon:
        name = name if name in cls.zukan else next(iter(cls.zukan))
        poke = Pokemon(cls.zukan[name])
        cls.init_kata(poke)
        return poke

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

    @classmethod
    def init_kata(cls, poke: Pokemon):
        poke.ability = cls.create_ability("")
        poke.item = cls.create_item("")

    @classmethod
    def reconstruct_pokemon_from_log(cls, data: dict) -> Pokemon:
        poke = cls.create_pokemon(data["name"])
        poke.gender = Gender[data["gender"]]
        poke.level = data["level"]
        poke.nature = data["nature"]
        poke.ability = cls.create_ability(data["ability"])
        poke.item = cls.create_item(data["item"])
        poke.moves = [cls.create_move(s) for s in data["moves"]]
        poke.indiv = data["indiv"]
        poke.effort = data["effort"]
        poke.terastal = data["terastal"]
        return poke
