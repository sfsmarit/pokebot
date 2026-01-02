from __future__ import annotations
from typing import TYPE_CHECKING, Any, Literal
if TYPE_CHECKING:
    from jpoke.core.battle import Battle

from jpoke.core.event import EventContext
from jpoke.utils.enums import Stat
from . import common


def reveal_ability(battle: Battle, ctx: EventContext, value: Any,
                   whose: Literal["self", "foe"] = "self"):
    return common.reveal(battle, ctx, value, what="ability", whose=whose)


def check_ability(battle: Battle, ctx: EventContext, value: Any,
                  ability: str, whose: Literal["self", "foe"] = "self"):
    mon = ctx.source if whose == "self" else battle.foe(ctx.source)
    return mon.ability == ability


def ありじごく(battle: Battle, ctx: EventContext, value: Any) -> bool:
    return not ctx.source.floating(battle.events)


def かげふみ(battle: Battle, ctx: EventContext, value: Any) -> bool:
    return ctx.source.ability != "かげふみ"


def じりょく(battle: Battle, ctx: EventContext, value: Any) -> bool:
    return "はがね" in ctx.source.types


def かちき(battle: Battle, ctx: EventContext, value: Any):
    if value < 0 and ctx.by_foe:
        battle.modify_stat(ctx.source, Stat.C, +2)
        reveal_ability(battle, ctx, value)
