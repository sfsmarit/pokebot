from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from jpoke.core.battle import Battle

from jpoke.utils.types import GLOBAL_FIELDS, SIDE_FIELDS
from jpoke.core.event import EventContext, HandlerResultFlag


def reduce_global_field_count(battle: Battle, value: Any,
                              ctx: EventContext, name: GLOBAL_FIELDS):
    if battle.field.reduce_count(battle.events, name):
        field = battle.field.fields[name]
        battle.add_turn_log(None, f"{field.name} 残り{field.count}ターン")
    return HandlerResultFlag.STOP_HANDLER


def reduce_side_field_count(battle: Battle, value: Any,
                            ctx: EventContext, name: SIDE_FIELDS):
    player = battle.find_player(ctx.source)
    side = battle.side(player)
    if side.reduce_count(battle.events, name):
        field = side.fields[name]
        battle.add_turn_log(None, f"{field.name} 残り{field.count}ターン")


def すなあらし(battle: Battle, value: Any, ctx: EventContext):
    if battle.modify_hp(ctx.source, r=-1/16):
        battle.add_turn_log(ctx.source, "すなあらしダメージ")


def グラスフィールド(battle: Battle, value: Any, ctx: EventContext):
    if battle.modify_hp(ctx.source, r=1/16):
        battle.add_turn_log(ctx.source, "グラスフィールド回復")
