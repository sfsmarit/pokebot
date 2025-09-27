from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle
    from pokebot.core.pokemon import Pokemon


def たべのこし(battle: Battle, user: Pokemon):
    if user.modify_hp(battle, int(user.max_hp/16)):
        battle.insert_turn_log(-1, battle.idx(user), user.item.name)
