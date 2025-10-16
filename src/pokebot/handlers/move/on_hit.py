from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Interrupt, Stat
from pokebot.core.events import EventContext


def modify_stat(battle: Battle, ctx: EventContext, move: str, stat: Stat, value: int):
    if ctx.source.field_status.executed_move == move and \
            battle.modify_stat(ctx.source, stat, value):
        battle.write_log(ctx.source, "追加効果")


def pivot(battle: Battle, ctx: EventContext, move: str):
    if ctx.source.field_status.executed_move == move:
        player = battle.get_player(ctx.source)
        battle.states[player].interrupt = Interrupt.PIVOT


def アームハンマー(battle: Battle, value: Any, ctx: EventContext):
    modify_stat(battle, ctx, "アームハンマー", Stat.S, -1)


def クイックターン(battle: Battle, value: Any, ctx: EventContext):
    return pivot(battle, ctx, "クイックターン")


def とんぼがえり(battle: Battle, value: Any, ctx: EventContext):
    return pivot(battle, ctx, "とんぼがえり")


def ボルトチェンジ(battle: Battle, value: Any, ctx: EventContext):
    return pivot(battle, ctx, "ボルトチェンジ")


def ふきとばし(battle: Battle, value: Any, ctx: EventContext):
    if ctx.source.field_status.executed_move == "ふきとばし":
        player = battle.get_player(ctx.source)
        commands = battle.get_available_switch_commands(player)
        command = battle.random.choice(commands)
        battle.run_switch(idx, player.team[command.idx])


def わるあがき(battle: Battle, value: Any, ctx: EventContext):
    if ctx.source.field_status.executed_move == "わるあがき" and \
            battle.modify_hp(ctx.source, -ctx.source.max_hp // 4):
        battle.write_log(ctx.source, "追加効果")
