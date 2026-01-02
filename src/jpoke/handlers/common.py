from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Any, TypedDict
if TYPE_CHECKING:
    from jpoke.core.battle import Battle
    from jpoke.core.event import EventContext

from jpoke.data.field import FIELDS
from jpoke.utils.enums import Stat
from jpoke.utils.types import AILMENT, WEATHER, TERRAIN, SIDE_FIELD


def reveal(
    battle: Battle, ctx: EventContext, value: Any,
    what: Literal["ability", "item", "move"],
    whose: Literal["self", "foe"],
) -> bool:
    mon = ctx.source if whose == "self" else battle.foe(ctx.source)
    match what:
        case "ability":
            target = mon.ability
        case "item":
            target = mon.item
        case "move":
            target = ctx.move
    target.observed = True
    battle.add_turn_log(ctx.source, target.name)
    return True


def modify_hp(
    battle: Battle, ctx: EventContext, value: Any,
    target_side: Literal["self", "foe"],
    v: int = 0,
    r: float = 0,
    prob: float = 1,
) -> bool:
    """HPが変化したらTrueを返す"""
    if prob < 1 and battle.random.random() >= prob:
        return False
    target = ctx.source if target_side == "self" else battle.foe(ctx.source)
    return battle.modify_hp(target, v, r)


def modify_stat(
    battle: Battle, ctx: EventContext, value: Any,
    target_side: Literal["self", "foe"],
    stat: Stat,
    v: int,
    prob: float = 1
) -> bool:
    """能力ランクが変化したらTrueを返す"""
    if prob < 1 and battle.random.random() >= prob:
        return False
    target = ctx.source if target_side == "self" else battle.foe(ctx.source)
    return battle.modify_stat(target, stat, v, by_foe=target_side == "foe")


def apply_ailment(
        battle: Battle, ctx: EventContext, value: Any,
        target_side: Literal["self", "foe"],
        ailment: AILMENT,
        prob: float = 1
) -> bool:
    if prob < 1 and battle.random.random() >= prob:
        return False
    target = ctx.source if target_side == "self" else battle.foe(ctx.source)
    if ailment:
        return target.ailment.overwrite(battle.events, ailment)
    else:
        return target.ailment.cure(battle.events)


def apply_weather(
    battle: Battle, ctx: EventContext, value: Any,
    name: WEATHER
):
    count = 5 + 3*(ctx.source.item == FIELDS[name].turn_extension_item)
    return battle.field.activate_weather(name, count)


def apply_terrain(
    battle: Battle, ctx: EventContext, value: Any,
    name: TERRAIN
):
    count = 5 + 3*(ctx.source.item == FIELDS[name].turn_extension_item)
    return battle.field.activate_terrain(name, count)


def apply_side_field(
    battle: Battle, ctx: EventContext, value: Any,
    target_side: Literal["self", "foe"],
    name: SIDE_FIELD,
    count: int = 1,
    extended_count: int | None = None
):
    target = ctx.source if target_side == "self" else battle.foe(ctx.source)
    player = battle.find_player(target)
    side = battle.side(player)
    if extended_count and ctx.source.item == side.fields[name].turn_extention_item:
        count = extended_count
    if side.activate(name, count):
        battle.add_turn_log(player, f"{name} {count}ターン")
