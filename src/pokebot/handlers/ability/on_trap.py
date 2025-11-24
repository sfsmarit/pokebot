from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.core.events import EventContext


def ありじごく(battle: Battle, value: Any, ctx: EventContext):
    ctx.source.field_status._trapped |= not battle.foe(ctx.source).floating(battle.events)


def かげふみ(battle: Battle, value: Any, ctx: EventContext):
    ctx.source.field_status._trapped |= battle.foe(ctx.source).ability != "かげふみ"


def じりょく(battle: Battle, value: Any, ctx: EventContext):
    ctx.source.field_status._trapped |= "はがね" in battle.foe(ctx.source).types
