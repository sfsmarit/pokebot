from __future__ import annotations
from typing import TYPE_CHECKING, Literal
if TYPE_CHECKING:
    from pokebot.core.events import EventManager
    from pokebot.player import Player

from copy import deepcopy

from pokebot.utils import copy_utils as copyut
from pokebot.model import Field


class GlobalFieldManager:
    def __init__(self, events: EventManager) -> None:
        self.events: EventManager = events
        self.actives: list[Field] = []

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        copyut.fast_copy(self, new, keys_to_deepcopy=["actives"])
        return new

    def update_reference(self, events: EventManager, players: list[Player]):
        self.events = events
        for field in self.actives:
            field.update_reference(players)

    def set_weather(self,
                    name: Literal["", "はれ", "あめ", "ゆき", "すなあらし"] = "",
                    count: int = 0,
                    ) -> bool:
        if not name or count == 0:
            # 天候の終了
            return self.weather.set_count(self.events, 0)
        elif name != self.weather.name:
            # 天候の変更
            return self.weather.set(self.events, name, count)
        return False

    def set_terrain(self,
                    name: Literal["", "エレキフィールド", "グラスフィールド", "サイコフィールド", "ミストフィールド"] = "",
                    count: int = 0,
                    ) -> bool:
        if not name or count == 0:
            # フィールドの終了
            return self.terrain.set_count(self.events, 0)
        elif name != self.terrain.name:
            # フィールドの変更
            return self.terrain.set(self.events, name, count)
        return False


class SideFieldManager:
    def __init__(self, events: EventManager) -> None:
        self.events: EventManager = events
        self.actives: list[Field] = []

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        copyut.fast_copy(self, new, keys_to_deepcopy=["actives"])
        return new

    def update_reference(self, events: EventManager, player: Player):
        self.events = events
        for field in self.actives:
            field.update_reference([player])
