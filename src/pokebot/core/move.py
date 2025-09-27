from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core import Battle, Pokemon

import pokebot.common.utils as ut
from pokebot.data.move import MoveData

from .base import Effect


class Move(Effect):
    def __init__(self, data: MoveData, pp: int | None = None):
        super().__init__(data)

        self.pp: int = pp if pp else data.pp

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new)
        return new

    def modify_pp(self, v: int):
        self.pp = max(0, min(self.data.pp, self.pp + v))
