import pokebot.common.utils as ut
from pokebot.data.registry import ItemData

from .effect import BaseEffect


class Item(BaseEffect):
    def __init__(self, data: ItemData) -> None:
        super().__init__(data)

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return ut.fast_copy(self, new)

    def consume(self):
        self.active = False
        self.observed = True
