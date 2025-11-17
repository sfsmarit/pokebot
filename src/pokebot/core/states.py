from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.events import EventManager

from typing import Literal

from pokebot.utils import copy_utils as ut
from pokebot.utils.enums import Command

from .events import Interrupt

from pokebot.model import Field


class PlayerState:
    def __init__(self) -> None:
        self.reset_game()
        self.reset_turn()

    def reset_game(self):
        self.selected_idxes: list[int] = []
        self.active_idx: int = None  # type: ignore
        self.interrupt: Interrupt = Interrupt.NONE
        self.reserved_commands: list[Command] = []

    def reset_turn(self):
        self.already_switched = False

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return ut.fast_copy(self, new)


class GlobalState:
    def __init__(self, events: EventManager) -> None:
        self.events = events
        self.reset_game()

    def reset_game(self):
        self.weather: Field = Field()
        self.terrain: Field = Field()
        self.gravity: Field = Field("じゅうりょく")
        self.trickroom: Field = Field("トリックルーム")

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return ut.fast_copy(self, new, ["weather", "terrain", "gravity", "trickroom"])

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
        return self.terrain.set(self.events, name, count)

    def set_gravity(self, count: int = 0) -> bool:
        return self.gravity.set_count(self.events, count)

    def set_trickroom(self, count: int = 0) -> bool:
        return self.trickroom.set_count(self.events, count)


class SideState:
    def __init__(self, events: EventManager) -> None:
        self.events = events
        self.reset_game()

    def reset_game(self):
        self.reflector: Field = Field("リフレクター")
        # self.reflector: Field = Field("ひかりのかべ")
        # self.reflector: Field = Field("オーロラベール")
        # self.reflector: Field = Field("しんぴのまもり")
        # self.reflector: Field = Field("しろいきり")
        # self.reflector: Field = Field("おいかぜ")
        # self.reflector: Field = Field("ねがいごと")
        # self.reflector: Field = Field("まきびし")
        # self.reflector: Field = Field("どくびし")
        # self.reflector: Field = Field("ステルスロック")
        # self.reflector: Field = Field("ねばねばネット")

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return ut.fast_copy(self, new, ["reflector"])

    def set_reflector(self, count: int = 0) -> bool:
        return self.reflector.set_count(self.events, count)
