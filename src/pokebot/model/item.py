from __future__ import annotations

import pokebot.common.utils as ut

from .base_data import ItemData


class Item:
    def __init__(self, data: ItemData):
        self.data: ItemData = data      # 静的データへの参照
        self.active: bool = True
        self.observed: bool = False

    def __str__(self):
        return self.name

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new)
        return new

    @property
    def name(self):
        return self.data.name
