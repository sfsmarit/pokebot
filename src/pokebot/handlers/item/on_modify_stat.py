from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Interrupt
from pokebot.core.events import EventContext
from .common import write_log_and_consume


def だっしゅつパック(battle: Battle, value: Any, ctx: EventContext):
    if ctx.source.item == "だっしゅつパック":
        player = battle.get_player(ctx.source)
        battle.states[player].interrupt = Interrupt.EJECTPACK_REQUESTED
        write_log_and_consume(battle, ctx.source)
