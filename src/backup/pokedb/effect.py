from __future__ import annotations

from typing import Literal

from pokebot.common.enums import Event, Ailment
from pokebot.common.constants import STAT_CODES


class Effect:
    def __init__(self) -> None:
        self.trigger: Event
        self.target: Literal["", "self", "opponent", "all"] = ""
        self.chance: float = 1.
        self.rank: list[int] = [0, 0, 0, 0, 0, 0, 0, 0]
        self.ailments: list[Ailment] = []
        self.confusion: bool = False
        self.flinch: bool = False
        self.drain: float = 0.
        self.recoil: float = 0.

    @classmethod
    def from_json(cls, data: dict) -> Effect:
        obj = cls()

        obj.trigger = Event(data["trigger"])

        for i, s in enumerate(STAT_CODES):
            if s in data:
                obj.rank[i] = data[s]

        for s in Ailment.names():
            if s in data:
                obj.ailments.append(Ailment[s])

        for key in ["target", "chance", "confusion", "flinch", "drain", "recoil"]:
            if key in data:
                setattr(obj, key, data[key])

        return obj
