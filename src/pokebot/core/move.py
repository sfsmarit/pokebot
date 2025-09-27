from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core import Battle, Pokemon

import pokebot.common.utils as ut
from pokebot.data.move import MoveData


class Move:
    def __init__(self, data: MoveData, pp: int | None = None):
        self.data: MoveData = data
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

    def register_handlers(self, battle: Battle):
        for event, func in self.data.handlers.items():
            battle.events.on(event, func)

    @property
    def name(self):
        return self.data.name

    def add_pp(self, v: int):
        self.pp = max(0, min(self.data.pp, self.pp + v))
