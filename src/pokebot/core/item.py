from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core import Battle, Pokemon

import pokebot.common.utils as ut
from pokebot.data.registry import ItemData

from .base import Effect


class Item(Effect):
    def __init__(self, data: ItemData) -> None:
        super().__init__(data)

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new)
        return new
