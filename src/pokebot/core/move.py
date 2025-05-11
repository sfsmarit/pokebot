from __future__ import annotations

from copy import deepcopy

from pokebot.common.enums import MoveCategory
import pokebot.common.utils as ut
from pokebot.core import PokeDB


class Move:
    """ポケモンの技を表現するクラス"""

    def __init__(self,
                 name: str = "",
                 pp: int = 0,
                 observed: bool = False):

        if name and name not in PokeDB.moves:
            print(f"{name} is not in PokeDB.moves")
            name = ""

        self.name: str = name
        self._org_pp = PokeDB.moves[name]["pp"] if name and pp == 0 else pp
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

    def set_base_info(self):
        self.type = PokeDB.moves[self.name]['type']
        self.category = PokeDB.moves[self.name]['category']
        self.power = PokeDB.moves[self.name]['power']
        self.hit = PokeDB.moves[self.name]['hit']
        self.priority = 0

        if self.name in PokeDB.move_priority:
            self.priority = PokeDB.move_priority[self.name]

        if self.category == MoveCategory.STA:
            self.protect = PokeDB.moves[self.name]["protect"]
            self.subst = PokeDB.moves[self.name]["subst"]
            self.gold = PokeDB.moves[self.name]["gold"]
            self.mirror = PokeDB.moves[self.name]["mirror"]

        for tag, val in PokeDB.move_tag.items():
            if self.name in val:
                self.tags.append(tag)

    def game_reset(self):
        """試合開始前の状態に初期化"""
        self.pp = self._org_pp
        self.observed = False

    def dump(self) -> dict:
        d = deepcopy(vars(self))
        d["category"] = d["category"].value
        return d

    def load(self, d: dict):
        self.__dict__ |= d
        self.category = MoveCategory(self.category)

    def add_pp(self, v: int):
        self.pp = max(0, min(self._org_pp, self.pp + v))
