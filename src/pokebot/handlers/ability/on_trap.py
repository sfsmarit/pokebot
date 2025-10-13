from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Stat, Ailment
from pokebot.core.events import EventContext


def ありじごく(battle: Battle, ctx: EventContext):
    ctx.source.field_status._trapped |= (
        ctx.source.ability == "ありじごく" and
        not battle.foe(ctx.source).floating(battle.events)
    )


def かげふみ(battle: Battle, ctx: EventContext):
    ctx.source.field_status._trapped |= (
        ctx.source.ability == "かげふみ" and
        battle.foe(ctx.source).ability != "かげふみ"
    )


def じりょく(battle: Battle, ctx: EventContext):
    ctx.source.field_status._trapped |= (
        ctx.source.ability == "かげふみ" and
        "はがね" in battle.foe(ctx.source).types
    )
