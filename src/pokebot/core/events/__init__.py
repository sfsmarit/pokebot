from .steps import Step


from typing import Callable
from enum import Enum, auto


class Event(Enum):
    ON_START = auto()
    ON_SWITCH_IN = auto()
    ON_BEFORE_MOVE = auto()
    ON_TRY_MOVE = auto()
    ON_HIT = auto()
    ON_DAMAGE = auto()
    ON_TURN_END = auto()
    ON_RANK_UP = auto()
    ON_RANK_DOWN = auto()
    ON_END = auto()


class EventManager:
    def __init__(self) -> None:
        self.handlers = {}

    def on(self, event: Event, func: Callable, once: bool = True):
        """イベントにハンドラを登録"""
        self.handlers.setdefault(event, []).append((func, once))

    def off(self, event: Event, func: Callable):
        if event in self.handlers:
            self.handlers[event] = [
                (f, o) for (f, o) in self.handlers[event] if f != func
            ]

    def emit(self, event: Event, *args, **kwargs):
        """イベントを発火"""
        for func, once in self.handlers.get(event, []):
            func(*args, **kwargs)
            if once:
                self.off(event, func)
