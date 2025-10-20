from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Stat
from pokebot.core.events import EventContext, Interrupt


def modify_stat(battle: Battle, ctx: EventContext, stat: Stat, value: int):
    if battle.modify_stat(ctx.source, stat, value):
        battle.add_turn_log(ctx.source, "追加効果")


def pivot(battle: Battle, ctx: EventContext):
    player = battle.find_player(ctx.source)
    if battle.get_available_switch_commands(player):
        battle.states[player].interrupt = Interrupt.PIVOT


def アームハンマー(battle: Battle, value: Any, ctx: EventContext):
    modify_stat(battle, ctx, Stat.S, -1)


def クイックターン(battle: Battle, value: Any, ctx: EventContext):
    return pivot(battle, ctx)


def とんぼがえり(battle: Battle, value: Any, ctx: EventContext):
    return pivot(battle, ctx)


def ボルトチェンジ(battle: Battle, value: Any, ctx: EventContext):
    return pivot(battle, ctx)


def ふきとばし(battle: Battle, value: Any, ctx: EventContext):
    player = battle.find_player(ctx.source)
    rival = battle.rival(player)
    commands = battle.get_available_switch_commands(rival)
    if commands:
        command = battle.random.choice(commands)
        battle.run_switch(rival, rival.team[command.idx])


def わるあがき(battle: Battle, value: Any, ctx: EventContext):
    if battle.modify_hp(ctx.source, -ctx.source.max_hp // 4):
        battle.add_turn_log(ctx.source, "反動")
