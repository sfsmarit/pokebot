from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Stat, Ailment
from pokebot.core.events import EventContext


def いかく(battle: Battle, value: Any, ctx: EventContext):
    if battle.modify_stat(battle.foe(ctx.source), Stat.A, -1, by_foe=True):
        battle.add_turn_log(ctx.source, ctx.source.ability.name)


def きんちょうかん(battle: Battle, value: Any, ctx: EventContext):
    battle.foe(ctx.source).field_status.nervous = True
    battle.add_turn_log(ctx.source, ctx.source.ability.name)


def ぜったいねむり(battle: Battle, value: Any, ctx: EventContext):
    ctx.source.ailment = Ailment.SLP
    battle.add_turn_log(ctx.source, ctx.source.ability.name)
