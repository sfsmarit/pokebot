from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core import Battle, Pokemon

import pokebot.common.utils as ut

from pokebot.data.registry import AbilityData


class Ability:
    def __init__(self, data: AbilityData):
        self.data: AbilityData = data      # 静的データへの参照
        self.active: bool = True
        self.observed: bool = False
        self.count: int = 0

    def __str__(self):
        return self.name

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new)
        return new

    def register_handlers(self, battle: Battle):
        for event, func in self.data.handlers.items():
            battle.events.on(event, func)

    @property
    def name(self):
        return self.data.name
