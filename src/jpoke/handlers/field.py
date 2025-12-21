from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from jpoke.core.battle import Battle

from jpoke.utils.types import GLOBAL_FIELD, SIDE_FIELD
from jpoke.core.event import EventContext, HandlerResultFlag


def リフレクター(battle: Battle, value: Any, ctx: EventContext):
    def_player = battle.rival(battle.find_player(ctx.source))
    r = 1
    if battle.side(def_player).fields["reflector"].count and ctx.move.category == "物理":
        r = 0.5
        battle.add_damage_log(ctx.source, f"リフレクター x{r}")
    return value * r


def reduce_global_field_count(battle: Battle, value: Any, ctx: EventContext,
                              name: GLOBAL_FIELD):
    if battle.field.reduce_count(battle.events, name):
        field = battle.field.fields[name]
        battle.add_turn_log(None, f"{field.name} 残り{field.count}ターン")
    return HandlerResultFlag.STOP_HANDLER


def reduce_side_field_count(battle: Battle, value: Any, ctx: EventContext,
                            name: SIDE_FIELD):
    player = battle.find_player(ctx.source)
    side = battle.side(player)
    if side.reduce_count(battle.events, name):
        field = side.fields[name]
        battle.add_turn_log(None, f"{field.name} 残り{field.count}ターン")
