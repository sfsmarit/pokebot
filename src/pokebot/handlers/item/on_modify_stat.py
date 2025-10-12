from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Breakpoint
from pokebot.core.events import EventContext
from .common import write_log_and_consume


def だっしゅつパック(battle: Battle, ctx: EventContext):
    if ctx.source.item == "だっしゅつパック":
        idx = battle.get_player_index(ctx.source)
        battle.breakpoint[idx] = Breakpoint.REQUESTED
        write_log_and_consume(battle, ctx.source)
