import pokebot.common.utils as ut
from pokebot.data.registry import AbilityData

from .base import Effect


class Ability(Effect):
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
        ut.selective_deepcopy(self, new)
        return new
