from __future__ import annotations
from typing import TYPE_CHECKING, Self
if TYPE_CHECKING:
    from pokebot.core.events import EventManager


class Effect:
    def __init__(self, data) -> None:
        self.data = data
        self.active: bool = True
        self.observed: bool = False

    @property
    def name(self):
        return self.data.name

    def register_handlers(self, events: EventManager):
        for event, handler in self.data.handlers.items():
            events.on(event, handler)

    def unregister_handlers(self, events: EventManager):
        for event, handler in self.data.handlers.items():
            events.off(event, handler)

    def __str__(self):
        return self.name

    def __eq__(self, value: Self | str) -> bool:
        if isinstance(value, str):
            return self.name == value
        else:
            return self is value

    def __nq__(self, value: Self | str) -> bool:
        if isinstance(value, str):
            return self.name != value
        else:
            return self is not value
