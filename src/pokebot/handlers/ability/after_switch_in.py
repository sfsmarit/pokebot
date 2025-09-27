from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle
    from pokebot.core.pokemon import Pokemon

from pokebot.common.enums import Stat


def いかく(battle: Battle, user: Pokemon):
    if battle.foe(user).active_status.change_rank(battle, Stat.A, -1):
        battle.insert_turn_log(-1, battle.idx(user), user.ability.name)
