from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle
    from pokebot.core.pokemon import Pokemon

from pokebot.common.enums import Stat


def アームハンマー(battle: Battle, source: Pokemon):
    if source.active_status.executed_move == "アームハンマー" and \
            source.active_status.modify_rank(battle, Stat.S, -1):
        battle.insert_turn_log(-1, source, "追加効果")
