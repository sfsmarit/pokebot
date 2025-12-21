from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Any
if TYPE_CHECKING:
    from jpoke.core.battle import Battle
    from jpoke.core.event import EventContext

from jpoke.data.field import FIELDS
from jpoke.utils.enums import Stat
from jpoke.utils.types import AILMENT, WEATHER, TERRAIN, SIDE_FIELD


def modify_hp(battle: Battle, value: Any, ctx: EventContext,
              target: Literal["self", "foe"], v: int = 0, r: float = 0,
              prob: float = 1, log: str = ""):
    if prob < 1 and battle.random.random() >= prob:
        return
    mon = ctx.source if target == "self" else battle.foe(ctx.source)
    if battle.modify_hp(mon, v, r) and log:
        battle.add_turn_log(mon, log)


def modify_stat(battle: Battle, value: Any, ctx: EventContext,
                target: Literal["self", "foe"], stat: Stat, v: int,
                prob: float = 1):
    if prob < 1 and battle.random.random() >= prob:
        return
    mon = ctx.source if target == "self" else battle.foe(ctx.source)
    by_foe = target == "foe"
    if battle.modify_stat(mon, stat, v, by_foe=by_foe):
        battle.add_turn_log(ctx.source, ctx.source.ability.name)


def apply_ailment(battle: Battle, value: Any, ctx: EventContext,
                  target: Literal["self", "foe"], ailment: AILMENT,
                  prob: float = 1):
    if prob < 1 and battle.random.random() >= prob:
        return
    mon = ctx.source if target == "self" else battle.foe(ctx.source)
    if not ailment:
        if mon.ailment.cure(battle.events):
            battle.add_turn_log(mon, "状態異常回復")
    else:
        if mon.ailment.overwrite(battle.events, ailment):
            battle.add_turn_log(mon, ailment)


def apply_weather(battle: Battle, value: Any, ctx: EventContext,
                  name: WEATHER):
    count = 5 + 3*(ctx.source.item == FIELDS[name].turn_extension_item)
    if battle.field.activate_weather(name, count):
        battle.add_turn_log(ctx.source, f"{battle.weather.name} {battle.weather.count}ターン")


def apply_terrain(battle: Battle, value: Any, ctx: EventContext,
                  name: TERRAIN):
    count = 5 + 3*(ctx.source.item == FIELDS[name].turn_extension_item)
    if battle.field.activate_terrain(name, count):
        battle.add_turn_log(ctx.source, f"{battle.terrain.name} {battle.terrain.count}ターン")


def apply_side_field(battle: Battle, value: Any, ctx: EventContext,
                     target: Literal["self", "foe"], name: SIDE_FIELD,
                     count: int = 1, extended_count: int | None = None):
    mon = ctx.source if target == "self" else battle.foe(ctx.source)
    player = battle.find_player(mon)
    side = battle.side(player)
    if extended_count and ctx.source.item == side.fields[name].turn_extention_item:
        count = extended_count
    if side.activate(name, count):
        battle.add_turn_log(player, f"{name} {count}ターン")
