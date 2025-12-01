from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.utils.enums import Stat
from pokebot.core.events import EventContext, Interrupt

from pokebot.handlers import common
from pokebot.data.field import FIELDS


def modify_stat(battle: Battle, ctx: EventContext, stat: Stat, value: int):
    if battle.modify_stat(ctx.source, stat, value):
        battle.add_turn_log(ctx.source, "追加効果")


def pivot(battle: Battle, ctx: EventContext):
    player = battle.find_player(ctx.source)
    if battle.get_available_switch_commands(player):
        battle.state(player).interrupt = Interrupt.PIVOT


def すなあらし(battle: Battle, value: Any, ctx: EventContext):
    common.change_weather("すなあらし", battle, ctx)


def アームハンマー(battle: Battle, value: Any, ctx: EventContext):
    modify_stat(battle, ctx, Stat.S, -1)


def クイックターン(battle: Battle, value: Any, ctx: EventContext):
    pivot(battle, ctx)


def どくどく(battle: Battle, value: Any, ctx: EventContext):
    common.apply_ailment(battle, "もうどく", battle.foe(ctx.source), ctx.source)


def とんぼがえり(battle: Battle, value: Any, ctx: EventContext):
    pivot(battle, ctx)


def ボルトチェンジ(battle: Battle, value: Any, ctx: EventContext):
    pivot(battle, ctx)


def ふきとばし(battle: Battle, value: Any, ctx: EventContext):
    player = battle.find_player(ctx.source)
    rival = battle.rival(player)
    commands = battle.get_available_switch_commands(rival)
    if commands:
        command = battle.random.choice(commands)
        battle.run_switch(rival, rival.team[command.idx])


def リフレクター(battle: Battle, value: Any, ctx: EventContext):
    field = "リフレクター"
    player = battle.find_player(ctx.source)
    count = 5 + 3*(ctx.source.item == FIELDS[field].turn_extension_item)
    if battle.side(player).reflector.set_count(battle.events, count):
        battle.add_turn_log(player, f"{field} {count}")


def わるあがき(battle: Battle, value: Any, ctx: EventContext):
    if battle.modify_hp(ctx.source, -ctx.source.max_hp // 4):
        battle.add_turn_log(ctx.source, "反動")
