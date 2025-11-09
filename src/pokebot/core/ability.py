import pokebot.utils.copy_utils as copyut
from pokebot.data.registry import AbilityData

from .effect import BaseEffect


class Ability(BaseEffect):
    def __init__(self, data: AbilityData) -> None:
        self.data: AbilityData
        super().__init__(data)

        self.bench_reset()

    def bench_reset(self):
        self.count: int = 0

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return copyut.fast_copy(self, new)
