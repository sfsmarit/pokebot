from __future__ import annotations
from typing import TYPE_CHECKING, Literal
if TYPE_CHECKING:
    from pokebot.core.battle import Battle
    from pokebot.core.events import EventContext
    from pokebot.model.pokemon import Pokemon

from pokebot.data.field import FIELDS


def apply_ailment(
    battle: Battle,
    ailment: Literal["", "どく", "もうどく", "まひ", "やけど", "こおり"],
    target: Pokemon,
    source: Pokemon,
):
    if target.ailment.change(battle.events, ailment):
        battle.add_turn_log(target, ailment)


def change_weather(name, battle: Battle, ctx: EventContext):
    count = 5 + 3*(ctx.source.item == FIELDS[name].turn_extension_item)
    if battle.set_weather(name, count):
        battle.add_turn_log(ctx.source, f"{battle.weather.name} {battle.weather.count}ターン")


def change_terrain(name, battle: Battle, ctx: EventContext):
    count = 5 + 3*(ctx.source.item == FIELDS[name].turn_extension_item)
    if battle.set_terrain(name, count):
        battle.add_turn_log(ctx.source, f"{battle.terrain.name} {battle.terrain.count}ターン")
