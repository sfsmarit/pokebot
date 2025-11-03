from __future__ import annotations

from copy import deepcopy

from pokebot.common.enums import MoveCategory
import pokebot.common.utils as ut

from .effect import Effect


class Move:
    """ポケモンの技を表現するクラス"""

    def __init__(self):
        self.name: str

        self.type: str
        self.category: MoveCategory
        self.power: int
        self._org_pp: int
        self.hit: int
        self.priority: int
        self.flags: list[str]
        self.effects: list[Effect]
        self.handlers: list

        self.observed: bool = False
        self.pp: int

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.fast_copy(self, new)
        return new

    def __str__(self):
        return self.name

    @classmethod
    def from_json(cls, data: dict) -> Move:
        obj = cls()
        obj.name = data["name"]
        obj.type = data["type"]
        obj.category = MoveCategory(data["category"])
        obj.org_pp = data["pp"]
        obj.power = data["power"]
        obj.hit = data["hit"]
        obj.priority = data["priority"]
        obj.flags = data["flags"]
        # obj.effects = [Effect.from_json(d) for d in data["effects"]]
        obj.handlers = data["handlers"]
        return obj

    @property
    def org_pp(self) -> int:
        return self._org_pp

    @org_pp.setter
    def org_pp(self, v: int):
        self._org_pp = self.pp = v

    def dump(self) -> dict:
        d = deepcopy(vars(self))
        d["category"] = d["category"].value
        return d

    def load(self, d: dict):
        self.__dict__ |= d
        self.category = MoveCategory(self.category)

    def init_game(self):
        """試合開始前の状態に初期化する"""
        self.pp = self._org_pp
        self.observed = False

    def add_pp(self, v: int):
        self.pp = max(0, min(self._org_pp, self.pp + v))
