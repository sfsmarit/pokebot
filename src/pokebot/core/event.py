from typing import Callable
from pokebot.common.enums import Event


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
