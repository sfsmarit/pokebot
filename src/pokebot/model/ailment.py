import pokebot.utils.copy_utils as copyut
from pokebot.data.ailment import AILMENTS

from .effect import BaseEffect


class Ailment(BaseEffect):
    def __init__(self, name: str = "") -> None:
        super().__init__(AILMENTS[name])

        self.bench_reset()

    def bench_reset(self):
        self.count: int = 0

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return copyut.fast_copy(self, new)
