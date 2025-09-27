from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle
    from pokebot.core.pokemon import Pokemon

from pokebot.common.enums import Stat


def かちき(battle: Battle, source: Pokemon):
    if source.ability == "かちき" and source.active_status.modify_rank(battle, Stat.C, +2):
        battle.insert_turn_log(-1, source, source.ability.name)
