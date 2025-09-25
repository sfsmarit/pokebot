from __future__ import annotations

import pokebot.common.utils as ut
from .base_data import MoveData


class Move:
    def __init__(self, data: MoveData, pp: int | None = None):
        self.data: MoveData = data              # 静的データへの参照
        self.pp: int = pp if pp else data.pp
        self.observed: bool = False

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new)
        return new

    def __str__(self):
        return self.name

    @property
    def name(self):
        return self.data.name

    def add_pp(self, v: int):
        self.pp = max(0, min(self.data.pp, self.pp + v))
