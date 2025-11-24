from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.events import EventManager
    from pokebot.player import Player

from pokebot.utils import copy_utils as copyut
from pokebot.data.field import FIELDS
from .effect import BaseEffect


class Field(BaseEffect):
    def __init__(self, owners: list[Player], name: str = "", count: int = 0) -> None:
        self.owners: list[Player] = owners
        self.init(name, count)

    def init(self, name: str, count: int):
        super().__init__(FIELDS[name])
        self.count = count
        self.observed = True

    @property
    def name(self) -> str:
        return self.data.name if self.active and self.count else ""

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return copyut.fast_copy(self, new)

    def set(self, events: EventManager, name: str, count: int) -> bool:
        # 現在のフィールドと異なるフィールド名を指定されたら、フィールドを上書きして終了する
        if name != self.name:
            for player in self.owners:
                self.unregister_handlers(events, player)
            self.init(name, count)
            for player in self.owners:
                self.register_handlers(events, player)
            return True

        if count == self.count:
            # カウントに変化がなければ中断
            return False
        elif count == 0:
            # フィールド解除
            self.count = count
            for player in self.owners:
                self.unregister_handlers(events, player)
            return True
        elif self.count:
            # カウントが残っている状態での重ねがけを禁止
            return False
        else:
            # フィールド発動
            self.count = count
            for player in self.owners:
                self.register_handlers(events, player)
            return True

    def set_count(self, events: EventManager, count: int) -> bool:
        return self.set(events, self.name, count)

    def reduce_count(self, events: EventManager, by: int = 1) -> bool:
        count = max(0, self.count - by)

        # カウントに変化がなければ中断
        if count == self.count:
            return False

        self.count = count
        if self.count == 0:
            for player in self.owners:
                self.unregister_handlers(events, player)  # フィールド解除
        return True
