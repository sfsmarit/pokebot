from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Stat
from pokebot.core.events import EventContext


def かちき(battle: Battle, ctx: EventContext):
    if ctx.source.ability == "かちき" and \
            ctx.value < 0 and \
            ctx.by_foe and \
            battle.modify_stat(ctx.source, Stat.C, +2):
        battle.add_turn_log(ctx.source, ctx.source.ability.name)
