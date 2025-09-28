from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Stat
from pokebot.core.events import EventContext


def いかく(battle: Battle, ctx: EventContext):
    if ctx.source.ability == "いかく" and \
            battle.foe(ctx.source).modify_rank(battle, Stat.A, -1, by_self=False):
        battle.insert_turn_log(-1, ctx.source, ctx.source.ability.name)


def きんちょうかん(battle: Battle, ctx: EventContext):
    if ctx.source.ability == "きんちょうかん":
        battle.foe(ctx.source).active_status.nervous = True
        battle.add_turn_log(ctx.source, ctx.source.ability.name)
