from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from jpoke.core.battle import Battle

from jpoke.utils.types import GLOBAL_FIELD, SIDE_FIELD
from jpoke.core.event import EventContext, HandlerResult


def reduce_global_field_count(battle: Battle, ctx: EventContext, value: Any,
                              name: GLOBAL_FIELD):
    if battle.field.reduce_count(name):
        field = battle.field.fields[name]
        battle.add_turn_log(None, f"{field.name} 残り{field.count}ターン")
    return HandlerResult.STOP_HANDLER


def reduce_side_field_count(battle: Battle, ctx: EventContext, value: Any,
                            name: SIDE_FIELD):
    player = battle.find_player(ctx.source)
    side = battle.side(player)
    if side.reduce_count(name):
        field = side.fields[name]
        battle.add_turn_log(None, f"{field.name} 残り{field.count}ターン")
