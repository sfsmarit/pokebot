from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle
    from pokebot.core.events import EventContext

from pokebot.data.field import FIELDS


def change_weather(name, battle: Battle, ctx: EventContext):
    obj = battle.global_state.weather
    count = 5 + 3*(ctx.source.item == FIELDS[name].turn_extension_item)
    if battle.global_state.set_weather(name, count):
        battle.add_turn_log(ctx.source, f"{obj.name} {obj.count}ターン")


def change_terrain(name, battle: Battle, ctx: EventContext):
    obj = battle.global_state.terrain
    count = 5 + 3*(ctx.source.item == FIELDS[name].turn_extension_item)
    if battle.global_state.set_terrain(name, count):
        battle.add_turn_log(ctx.source, f"{obj.name} {obj.count}ターン")
