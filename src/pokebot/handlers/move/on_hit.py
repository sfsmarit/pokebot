from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle
    from pokebot.core.pokemon import Pokemon

from pokebot.common.enums import Stat


def アームハンマー(battle: Battle, user: Pokemon):
    if user.active_status.change_rank(battle, Stat.S, -1):
        battle.insert_turn_log(-1, battle.idx(user), "追加効果")
