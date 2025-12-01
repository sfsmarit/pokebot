from __future__ import annotations
from typing import TYPE_CHECKING, TypedDict
if TYPE_CHECKING:
    from pokebot.core.events import EventManager
    from pokebot.player import Player

from pokebot.utils import copy_utils as copyut
from pokebot.utils.types import GLOBAL_FIELDS, WEATHERS, TERRAINS
from pokebot.model import Field


class GlobalFields(TypedDict):
    weather: Field
    terrain: Field
    gravity: Field
    trickroom: Field


class GlobalFieldManager:
    def __init__(self, events: EventManager, players: list[Player]) -> None:
        self.events: EventManager = events
        self.fields: GlobalFields = {
            "weather": Field(players),
            "terrain": Field(players),
            "gravity": Field(players, "じゅうりょく"),
            "trickroom": Field(players, "トリックルーム"),
        }

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        copyut.fast_copy(self, new, keys_to_deepcopy=["fields"])
        return new

    def update_reference(self, events: EventManager, players: list[Player]):
        self.events = events
        for field in self.fields.values():
            field.update_reference(players)  # type: ignore

    def activate_weather(self, name: WEATHERS, count: int) -> bool:
        field = self.fields["weather"]

        # 重ねがけ不可
        if name == field.name:
            return False

        if not name or count == 0:
            field.deactivate(self.events)
        else:
            field.overwrite(self.events, name, count)

        return True

    def activate_terrain(self, name: TERRAINS, count: int) -> bool:
        field = self.fields["terrain"]

        # 重ねがけ不可
        if name == field.name:
            return False

        if not name or count == 0:
            field.deactivate(self.events)
        else:
            field.overwrite(self.events, name, count)

        return True

    def deactivate(self, events: EventManager, name: GLOBAL_FIELDS) -> bool:
        field = self.fields[name]
        if field.count:
            field.deactivate(events)
            return True
        return False

    def reduce_count(self, events: EventManager,
                     name: GLOBAL_FIELDS, by: int = 1) -> bool:
        field = self.fields[name]
        new_count = max(0, field.count - by)
        if new_count != field.count:
            field.reduce_count(events)
            return True
        return False
