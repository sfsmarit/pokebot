from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.core import PokeDB
from pokebot.core import Move
from pokebot.logger import TurnLog


def _check_flinch(self: TurnManager,
                  atk: PlayerIndex,
                  move: Move) -> bool:

    attacker = self.battle.pokemon[atk]
    attacker_mgr = self.battle.poke_mgr[atk]
    defender_mgr = self.battle.poke_mgr[not atk]

    if not defender_mgr.can_be_flinched():
        return False

    prob = PokeDB.get_move_effect_value(move, "flinch")

    if prob:
        if attacker.ability.name == 'てんのめぐみ':
            prob *= 2

        if self.battle.random.random() < prob:
            self.battle.logger.append(TurnLog(self.battle.turn, atk, '追加効果 ひるみ'))
            return True

    elif defender_mgr.can_receive_move_effect(move):
        # 技以外のひるみ判定
        if attacker.ability.name == 'あくしゅう' and \
                attacker_mgr.activate_ability():
            self.battle.logger.append(TurnLog(self.battle.turn, atk, '追加効果 ひるみ'))
            return True

        elif attacker.item.name in ['おうじゃのしるし', 'するどいキバ'] and \
                attacker_mgr.activate_item():
            self.battle.logger.append(TurnLog(self.battle.turn, atk, '追加効果 ひるみ'))
            return True

    return False
