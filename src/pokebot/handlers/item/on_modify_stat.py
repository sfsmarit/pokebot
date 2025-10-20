from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.core.events import EventContext, Interrupt
from .common import write_log_and_consume


def だっしゅつパック(battle: Battle, value: Any, ctx: EventContext):
    player = battle.find_player(ctx.source)
    if battle.get_available_switch_commands(player):
        battle.states[player].interrupt = Interrupt.REQUESTED
