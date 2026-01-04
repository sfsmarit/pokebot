import jpoke.utils.copy_utils as copyut
from jpoke.data import ABILITIES

from .effect import BaseEffect


class Ability(BaseEffect):
    def __init__(self, name: str = "") -> None:
        super().__init__(ABILITIES[name])

        self.bench_reset()

    def bench_reset(self):
        self.count: int = 0

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return copyut.fast_copy(self, new)
