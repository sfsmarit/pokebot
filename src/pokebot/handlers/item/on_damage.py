from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Interrupt
from pokebot.core.events import EventContext
from .common import write_log_and_consume


def だっしゅつボタン(battle: Battle, ctx: EventContext):
    target = battle.foe(ctx.source)
    if target.item == "だっしゅつボタン":
        idx = battle.get_player_index(target)
        battle.interrupt[idx] = Interrupt.EJECTBUTTON
        write_log_and_consume(battle, target)
