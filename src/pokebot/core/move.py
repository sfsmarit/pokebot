from __future__ import annotations

import pokebot.common.utils as ut
from pokebot.data.move import MoveData


class Move:
    def __init__(self, name, data: MoveData, pp: int | None = None):
        self.name: str = name
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

    def add_pp(self, v: int):
        self.pp = max(0, min(self.data.pp, self.pp + v))
