from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Interrupt
from pokebot.core.events import EventContext
from .common import write_log_and_consume


def だっしゅつボタン(battle: Battle, value: Any, ctx: EventContext):
    target = battle.foe(ctx.source)
    if target.item == "だっしゅつボタン":
        player = battle.get_player(target)
        battle.states[player].interrupt = Interrupt.EJECTBUTTON
        write_log_and_consume(battle, target)
