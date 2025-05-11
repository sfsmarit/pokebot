from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.core import Move
from pokebot.logger import TurnLog


def _process_on_miss(self: TurnManager,
                     atk: PlayerIndex,
                     move: Move):
    """技が外れたときの処理"""
    battle = self.battle
    attacker = battle.pokemon[atk]
    attacker_mgr = battle.poke_mgr[atk]

    battle.logger.append(TurnLog(battle.turn, atk, 'はずれ'))
    attacker_mgr.unresponsive_turn = 0
    self.move_succeeded[atk] = False

    # 反動
    attacker_mgr.apply_move_recoil(move, 'mis_recoil')

    # からぶりほけんが発動したら、技は成功したとみなす
    if attacker.item.name == "からぶりほけん" and \
            attacker_mgr.activate_item(move):
        self.move_succeeded[atk] = True
