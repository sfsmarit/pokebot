from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from jpoke.core.battle import Battle

from jpoke.model.pokemon import Pokemon


def write_log_and_consume(battle: Battle, target: Pokemon):
    player = battle.find_player(target)
    if target.item.data.consumable:
        battle.add_turn_log(player, f"{target.item.name}消費")
        target.item.consume()
    else:
        battle.add_turn_log(player, f"{target.item.name}発動")
