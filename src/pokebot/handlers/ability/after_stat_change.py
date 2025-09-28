from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Stat
from pokebot.core.events import EventContext


def かちき(battle: Battle, ctx: EventContext):
    if ctx.source.ability == "かちき" and \
            ctx.value["value"] < 0 and \
            not ctx.value["by_self"] and \
            ctx.source.modify_rank(battle, Stat.C, +2):
        battle.insert_turn_log(-1, ctx.source, ctx.source.ability.name)
