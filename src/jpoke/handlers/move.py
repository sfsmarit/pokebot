from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from jpoke.core.battle import Battle

from jpoke.core.event import EventContext, Interrupt


def pivot(battle: Battle, value: Any, ctx: EventContext):
    player = battle.find_player(ctx.source)
    if battle.get_available_switch_commands(player):
        battle.state(player).interrupt = Interrupt.PIVOT


def blow(battle: Battle, value: Any, ctx: EventContext):
    player = battle.find_player(ctx.source)
    rival = battle.rival(player)
    commands = battle.get_available_switch_commands(rival)
    if commands:
        command = battle.random.choice(commands)
        battle.run_switch(rival, rival.team[command.idx])
