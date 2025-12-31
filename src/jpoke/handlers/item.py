from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from jpoke.core.battle import Battle
    from jpoke.model import Pokemon

from jpoke.core.event import EventContext, HandlerResult, Interrupt


def だっしゅつボタン(battle: Battle, ctx: EventContext, value: Any):
    target = battle.foe(ctx.source)
    if target.item == "だっしゅつボタン":
        player = battle.find_player(target)
        battle.state(player).interrupt = Interrupt.EJECTBUTTON


def だっしゅつパック(battle: Battle, ctx: EventContext, value: Any):
    player = battle.find_player(ctx.source)
    if battle.get_available_switch_commands(player):
        battle.state(player).interrupt = Interrupt.REQUESTED
