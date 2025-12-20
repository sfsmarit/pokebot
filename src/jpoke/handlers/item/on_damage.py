from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from jpoke.core.battle import Battle

from jpoke.core.event import EventContext, Interrupt
from .common import write_log_and_consume


def だっしゅつボタン(battle: Battle, value: Any, ctx: EventContext):
    target = battle.foe(ctx.source)
    if target.item == "だっしゅつボタン":
        player = battle.find_player(target)
        battle.states[player].interrupt = Interrupt.EJECTBUTTON
