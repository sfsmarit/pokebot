from typing import Literal
from pokebot.utils import copy_utils as copyut

from pokebot.core.events import EventManager
from pokebot.data.field import FIELDS

from .effect import BaseEffect


class Field(BaseEffect):
    def __init__(self, name: str = "", count: int = 0) -> None:
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
        # フィールド名に指定があれば必ず変更する
        if name != self.name:
            self.unregister_handlers(events)
            self.init(name, count)
            self.register_handlers(events)
            return True

        if count == self.count:
            # カウントに変化がなければ中断
            return False
        elif count == 0:
            # フィールド解除
            self.count = count
            self.unregister_handlers(events)
            return True
        elif self.count:
            # 重ねがけ不可
            return False
        else:
            # フィールド発動
            self.count = count
            self.register_handlers(events)
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
            self.unregister_handlers(events)  # フィールド解除
        return True
