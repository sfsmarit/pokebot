from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Stat, Ailment
from pokebot.core.events import EventContext


def いかく(battle: Battle, value: Any, ctx: EventContext):
    if ctx.source.ability == "いかく" and \
            battle.modify_stat(battle.foe(ctx.source), Stat.A, -1, by_foe=True):
        battle.write_log(ctx.source, ctx.source.ability.name)


def きんちょうかん(battle: Battle, value: Any, ctx: EventContext):
    if ctx.source.ability == "きんちょうかん":
        battle.foe(ctx.source).field_status.nervous = True
        battle.write_log(ctx.source, ctx.source.ability.name)


def ぜったいねむり(battle: Battle, value: Any, ctx: EventContext):
    if ctx.source.ability == "ぜったいねむり":
        ctx.source.ailment = Ailment.SLP
        battle.write_log(ctx.source, ctx.source.ability.name)
