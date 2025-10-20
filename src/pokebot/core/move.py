from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.events import EventManager

import pokebot.common.utils as ut
from pokebot.common.enums import MoveCategory
from pokebot.data.move import MoveData

from .effect import BaseEffect


class Move(BaseEffect):
    def __init__(self, data: MoveData, pp: int | None = None):
        self.data: MoveData
        super().__init__(data)

        self.pp: int = pp if pp else data.pp
        self.bench_reset()

    def bench_reset(self):
        self._type: str = self.data.type
        self._category: MoveCategory = self.data.category

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return ut.fast_copy(self, new)

    def modify_pp(self, v: int):
        self.pp = max(0, min(self.data.pp, self.pp + v))

    @property
    def type(self) -> str:
        return self._type

    @property
    def category(self) -> MoveCategory:
        return self._category
