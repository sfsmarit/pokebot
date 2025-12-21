from __future__ import annotations
from typing import TYPE_CHECKING, TypedDict
if TYPE_CHECKING:
    from jpoke.core.event import EventManager
    from jpoke.player import Player

from jpoke.utils import copy_utils as copyut
from jpoke.utils.types import GLOBAL_FIELD, WEATHER, TERRAIN
from jpoke.model import Field


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

    def activate_weather(self, name: WEATHER, count: int) -> bool:
        field = self.fields["weather"]

        # 重ねがけ不可
        if name == field.name:
            return False

        if not name or count == 0:
            field.deactivate(self.events)
        else:
            field.overwrite(self.events, name, count)

        return True

    def activate_terrain(self, name: TERRAIN, count: int) -> bool:
        field = self.fields["terrain"]

        # 重ねがけ不可
        if name == field.name:
            return False

        if not name or count == 0:
            field.deactivate(self.events)
        else:
            field.overwrite(self.events, name, count)

        return True

    def deactivate(self, name: GLOBAL_FIELD) -> bool:
        field = self.fields[name]
        if field.count:
            field.deactivate(self.events)
            return True
        return False

    def reduce_count(self, name: GLOBAL_FIELD, by: int = 1) -> bool:
        field = self.fields[name]
        new_count = max(0, field.count - by)
        if new_count != field.count:
            field.reduce_count(self.events)
            return True
        return False
