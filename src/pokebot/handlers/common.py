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
    if not ailment:
        if target.ailment.cure(battle.events):
            battle.add_turn_log(target, "状態異常回復")
    else:
        if target.ailment.overwrite(battle.events, ailment):
            battle.add_turn_log(target, ailment)


def activate_weather(battle: Battle, ctx: EventContext, name):
    count = 5 + 3*(ctx.source.item == FIELDS[name].turn_extension_item)
    if battle.field.activate_weather(name, count):
        battle.add_turn_log(ctx.source, f"{battle.weather.name} {battle.weather.count}ターン")


def activate_terrain(battle: Battle, ctx: EventContext, name):
    count = 5 + 3*(ctx.source.item == FIELDS[name].turn_extension_item)
    if battle.field.activate_terrain(name, count):
        battle.add_turn_log(ctx.source, f"{battle.terrain.name} {battle.terrain.count}ターン")
