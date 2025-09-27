from __future__ import annotations
from typing import TYPE_CHECKING, Self
if TYPE_CHECKING:
    from pokebot.core import Battle


class Effect:
    def __init__(self, data) -> None:
        self.data = data
        self.active: bool = True
        self.observed: bool = False

    @property
    def name(self):
        return self.data.name

    def register_handlers(self, battle: Battle):
        for event, func in self.data.handlers.items():
            battle.events.on(event, func)

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
