from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from jpoke.core.battle import Battle

from jpoke.core.event import EventContext
from jpoke.utils.enums import Stat


def notify(battle: Battle, ctx: EventContext, value: Any):
    battle.add_turn_log(ctx.source, ctx.source.ability.name)


def check_foe(battle: Battle, ctx: EventContext, value: Any, ability: str):
    return battle.foe(ctx.source).ability == ability


def ありじごく(battle: Battle, ctx: EventContext, value: Any):
    return not battle.foe(ctx.source).floating(battle.events)


def かげふみ(battle: Battle, ctx: EventContext, value: Any):
    return battle.foe(ctx.source).ability != "かげふみ"


def じりょく(battle: Battle, ctx: EventContext, value: Any):
    return "はがね" in battle.foe(ctx.source).types


def かちき(battle: Battle, ctx: EventContext, value: Any):
    if value < 0 and ctx.by_foe and \
            battle.modify_stat(ctx.source, Stat.C, +2):
        battle.add_turn_log(ctx.source, ctx.source.ability.name)
