from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle
    from pokebot.core.pokemon import Pokemon


def いのちのたま(battle: Battle, source: Pokemon):
    if source.item == "いのちのたま" and source.modify_hp(battle, -source.max_hp // 8):
        battle.insert_turn_log(-1, source, source.item.name)
