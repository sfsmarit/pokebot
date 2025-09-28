from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Stat
from pokebot.core.events import EventContext


def アームハンマー(battle: Battle, ctx: EventContext):
    if ctx.source.active_status.executed_move == "アームハンマー" and \
            ctx.source.modify_rank(battle, Stat.S, -1):
        battle.insert_turn_log(-1, ctx.source, "追加効果")
