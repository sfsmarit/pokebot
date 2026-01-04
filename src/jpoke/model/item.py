import jpoke.utils.copy_utils as copyut
from jpoke.data import ITEMS

from .effect import BaseEffect


class Item(BaseEffect):
    def __init__(self, name: str = "") -> None:
        super().__init__(ITEMS[name])

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return copyut.fast_copy(self, new)

    def consume(self):
        self.active = False
        self.observed = True
