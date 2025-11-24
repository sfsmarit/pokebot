from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.events import EventManager
    from pokebot.model.pokemon import Pokemon

import pokebot.utils.copy_utils as copyut
from pokebot.data.ailment import AILMENTS

from .effect import BaseEffect


class Ailment(BaseEffect):
    def __init__(self, owner: Pokemon, name: str = "") -> None:
        self.owner: Pokemon = owner
        self.init(name)
        self.observed = True

    def init(self, name: str):
        super().__init__(AILMENTS[name])
        self.bench_reset()

    def bench_reset(self):
        self.count: int = 0

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return copyut.fast_copy(self, new)

    def change(self, events: EventManager, name: str = "", forced: bool = False) -> bool:
        # 状態異常の上書きを禁止
        if not forced and self.name:
            return False

        # 変化がなければ中断
        if name == self.name:
            return False

        self.unregister_handlers(events, self.owner)
        self.init(name)
        self.register_handlers(events, self.owner)
        return True
