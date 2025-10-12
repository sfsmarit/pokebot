from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Stat, Ailment
from pokebot.core.events import EventContext


def いかく(battle: Battle, ctx: EventContext):
    if ctx.source.ability == "いかく" and \
            battle.foe(ctx.source).modify_stat(battle, Stat.A, -1, by_self=False):
        battle.add_turn_log(ctx.source, ctx.source.ability.name)


def きんちょうかん(battle: Battle, ctx: EventContext):
    if ctx.source.ability == "きんちょうかん":
        battle.foe(ctx.source).field_status.nervous = True
        battle.add_turn_log(ctx.source, ctx.source.ability.name)


def ぜったいねむり(battle: Battle, ctx: EventContext):
    if ctx.source.ability == "ぜったいねむり":
        ctx.source.ailment = Ailment.SLP
        battle.add_turn_log(ctx.source, ctx.source.ability.name)
