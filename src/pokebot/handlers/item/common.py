from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.core.pokemon import Pokemon


def write_log_and_consume(battle: Battle, target: Pokemon):
    if target.item.data.consumable:
        battle.add_turn_log(target, f"{target.item}消費")
        target.item.consume()
    else:
        battle.add_turn_log(target, f"{target.item}発動")
