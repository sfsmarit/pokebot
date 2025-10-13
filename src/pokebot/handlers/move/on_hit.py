from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Breakpoint, Stat
from pokebot.core.events import EventContext


def modify_stat(battle: Battle, ctx: EventContext, move: str, stat: Stat, value: int):
    if ctx.source.field_status.executed_move == move and \
            battle.modify_stat(ctx.source, stat, value):
        battle.add_turn_log(ctx.source, "追加効果")


def pivot(battle: Battle, ctx: EventContext, move: str):
    if ctx.source.field_status.executed_move == move:
        idx = battle.get_player_index(ctx.source)
        battle.breakpoint[idx] = Breakpoint.PIVOT


def アームハンマー(battle: Battle, ctx: EventContext):
    modify_stat(battle, ctx, "アームハンマー", Stat.S, -1)


def クイックターン(battle: Battle, ctx: EventContext):
    return pivot(battle, ctx, "クイックターン")


def とんぼがえり(battle: Battle, ctx: EventContext):
    return pivot(battle, ctx, "とんぼがえり")


def ボルトチェンジ(battle: Battle, ctx: EventContext):
    return pivot(battle, ctx, "ボルトチェンジ")


def ふきとばし(battle: Battle, ctx: EventContext):
    if ctx.source.field_status.executed_move == "ふきとばし":
        idx = not battle.get_player_index(ctx.source)
        switches = battle.get_available_switch_commands(battle.player[idx])
        command = battle.random.choice(switches)
        new = battle.player[idx].team[command.idx]
        battle.run_switch(idx, new)


def わるあがき(battle: Battle, ctx: EventContext):
    if ctx.source.field_status.executed_move == "わるあがき" and \
            battle.modify_hp(ctx.source, -ctx.source.max_hp // 4):
        battle.add_turn_log(ctx.source, "追加効果")
