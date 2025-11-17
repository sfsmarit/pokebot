from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.core.events import EventContext, HandlerResult


def reduce_weather_count(battle: Battle, value: Any, ctx: EventContext):
    obj = battle.global_state.weather
    if (s := obj.name) and obj.reduce_count(battle.events):
        battle.add_turn_log(None, f"{s} 残り{obj.count}ターン")
    return HandlerResult.STOP_HANDLER


def reduce_terrain_count(battle: Battle, value: Any, ctx: EventContext):
    obj = battle.global_state.terrain
    if (s := obj.name) and obj.reduce_count(battle.events):
        battle.add_turn_log(None, f"{s} 残り{obj.count}ターン")
    return HandlerResult.STOP_HANDLER


def すなあらし(battle: Battle, value: Any, ctx: EventContext):
    if battle.modify_hp(ctx.source, r=-1/16):
        battle.add_turn_log(ctx.source, "すなあらしダメージ")


def グラスフィールド(battle: Battle, value: Any, ctx: EventContext):
    if battle.modify_hp(ctx.source, r=1/16):
        battle.add_turn_log(ctx.source, "グラスフィールド回復")
