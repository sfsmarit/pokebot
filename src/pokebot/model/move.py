from __future__ import annotations

from copy import deepcopy

from pokebot.common.enums import MoveCategory
import pokebot.common.utils as ut
from pokebot.common import PokeDB


class Move:
    """ポケモンの技を表現するクラス"""

    def __init__(self,
                 name: str = "",
                 pp: int = 0,
                 observed: bool = False):

        if name and name not in PokeDB.move_data:
            print(f"{name} is not in PokeDB.moves")
            name = ""

        self.name: str = name
        self._org_pp = PokeDB.move_data[name].pp if name and pp == 0 else pp
        self.pp: int = self._org_pp
        self.observed = observed

        self.type: str = ""
        self.category: MoveCategory = MoveCategory.NONE
        self.power: int = 0
        self.hit: int = 0
        self.priority: int = 0
        self.tags: list[str] = []

        self.protect: bool = False
        self.subst: bool = False
        self.gold: bool = False
        self.mirror: bool = False

        if name:
            self.set_base_info()

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new)
        return new

    def __str__(self):
        return self.name

    def dump(self) -> dict:
        d = deepcopy(vars(self))
        d["category"] = d["category"].value
        return d

    def load(self, d: dict):
        self.__dict__ |= d
        self.category = MoveCategory(self.category)

    def set_base_info(self):
        self.type = PokeDB.move_data[self.name].type
        self.category = PokeDB.move_data[self.name].category
        self.power = PokeDB.move_data[self.name].power
        self.hit = PokeDB.move_data[self.name].hit
        self.priority = 0

        if self.name in PokeDB.move_priority:
            self.priority = PokeDB.move_priority[self.name]

        if self.category == MoveCategory.STA:
            self.protect = PokeDB.move_data[self.name].protect
            self.subst = PokeDB.move_data[self.name].subst
            self.gold = PokeDB.move_data[self.name].gold
            self.mirror = PokeDB.move_data[self.name].mirror

        for tag, val in PokeDB.tagged_moves.items():
            if self.name in val:
                self.tags.append(tag)

    def init_game(self):
        """試合開始前の状態に初期化する"""
        self.pp = self._org_pp
        self.observed = False

    def add_pp(self, v: int):
        """PPを加算する"""
        self.pp = max(0, min(self._org_pp, self.pp + v))
