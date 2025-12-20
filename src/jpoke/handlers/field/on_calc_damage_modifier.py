from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from jpoke.core.battle import Battle

from jpoke.core.event import EventContext, HandlerResultFlag


def リフレクター(battle: Battle, value: Any, ctx: EventContext):
    def_player = battle.rival(battle.find_player(ctx.source))
    r = 1
    if battle.side(def_player).reflector.count and ctx.move.category == "物理":
        r = 0.5
        battle.add_damage_log(ctx.source, f"リフレクター x{r}")
    return value * r
