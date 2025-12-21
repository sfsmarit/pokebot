from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from jpoke.core.battle import Battle

from jpoke.core.event import EventContext
from jpoke.utils.enums import Stat


def かちき(battle: Battle, value: Any, ctx: EventContext):
    if value < 0 and ctx.by_foe and \
            battle.modify_stat(ctx.source, Stat.C, +2):
        battle.add_turn_log(ctx.source, ctx.source.ability.name)


def きんちょうかん(battle: Battle, value: Any, ctx: EventContext):
    battle.foe(ctx.source).field_status.nervous = True
    battle.add_turn_log(ctx.source, ctx.source.ability.name)


def ありじごく(battle: Battle, value: Any, ctx: EventContext):
    ctx.source.field_status._trapped |= not battle.foe(ctx.source).floating(battle.events)


def かげふみ(battle: Battle, value: Any, ctx: EventContext):
    ctx.source.field_status._trapped |= battle.foe(ctx.source).ability != "かげふみ"


def じりょく(battle: Battle, value: Any, ctx: EventContext):
    ctx.source.field_status._trapped |= "はがね" in battle.foe(ctx.source).types
