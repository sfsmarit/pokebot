from __future__ import annotations
from typing import TYPE_CHECKING, TypedDict
if TYPE_CHECKING:
    from pokebot.core.event import EventManager
    from pokebot.player import Player

from pokebot.utils import copy_utils as copyut
from pokebot.utils.types import SIDE_FIELDS
from pokebot.model import Field


class SideFields(TypedDict):
    reflector: Field
    lightwall: Field
    shinpi: Field
    whitemist: Field
    oikaze: Field
    wish: Field
    makibishi: Field
    dokubishi: Field
    stealthrock: Field
    nebanet: Field


class SideFieldManager:
    def __init__(self, events: EventManager, player: Player) -> None:
        self.events: EventManager = events
        self.fields: SideFields = {
            "reflector": Field([player], "リフレクター"),
            "lightwall": Field([player], "ひかりのかべ"),
            "shinpi": Field([player], "しんぴのまもり"),
            "whitemist": Field([player], "しろいきり"),
            "oikaze": Field([player], "おいかぜ"),
            "wish": Field([player], "ねがいごと"),
            "makibishi": Field([player], "まきびし"),
            "dokubishi": Field([player], "どくびし"),
            "stealthrock": Field([player], "ステルスロック"),
            "nebanet": Field([player], "ねばねばネット"),
        }

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        copyut.fast_copy(self, new, keys_to_deepcopy=["fields"])
        return new

    def update_reference(self, events: EventManager, player: Player):
        self.events = events
        for field in self.fields.values():
            field.update_reference([player])  # type: ignore

    def activate(self, events: EventManager,
                 name: SIDE_FIELDS, count: int) -> bool:
        if not self.fields[name].count:
            self.fields[name].activate(events, count)
            return True
        return False

    def deactivate(self, events: EventManager, name: SIDE_FIELDS) -> bool:
        if self.fields[name].count:
            self.fields[name].deactivate(events)
            return True
        return False

    def reduce_count(self, events: EventManager,
                     name: SIDE_FIELDS, by: int = 1) -> bool:
        field = self.fields[name]
        new_count = max(0, field.count - by)
        if new_count != field.count:
            field.reduce_count(events, by)
            return True
        return False
