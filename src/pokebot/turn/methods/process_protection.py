from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import MoveCategory
from pokebot.core import Move
from pokebot.logger import TurnLog
from pokebot.move import effective_move_category


def _process_protection(self: TurnManager,
                        atk: PlayerIndex,
                        move: Move) -> bool:
    """
    まもる系の技の処理を行い、まもるが成功したらTrueを返す

    Parameters
    ----------
    atk_idx : int
        攻撃側のプレイヤーインデックス
    move : Move
        攻撃技

    Returns
    ----------
    bool
        まもるが成功したらTrue
    """
    battle = self.battle

    dfn = PlayerIndex(not atk)
    attacker = battle.pokemon[atk]
    attacker_mgr = battle.poke_mgr[atk]
    defender_mgr = battle.poke_mgr[dfn]

    if not self._protecting_move.name:
        return False

    # まもる貫通
    if 'anti_protect' in move.tags or \
            (attacker.ability.name == 'ふかしのこぶし' and attacker_mgr.contacts(move)):
        self.move_succeeded[dfn] = False
        return False

    move_category = effective_move_category(battle, atk, move)

    # 攻撃技かどうか
    self.move_succeeded[dfn] = move_category != MoveCategory.STA

    # 相手に影響を与える変化技かどうか
    if self._protecting_move.name != 'かえんのまもり':
        self.move_succeeded[dfn] |= "protect" in move.tags

    # まもる成功
    if not self.move_succeeded[dfn]:
        return False

    # 接触時の追加効果
    if attacker_mgr.contacts(move):
        defender_mgr.activate_move_effect(self._protecting_move)

    # 攻撃失敗による反動
    attacker_mgr.apply_move_recoil(move, 'mis_recoil')

    attacker_mgr.unresponsive_turn = 0
    battle.logger.append(TurnLog(battle.turn, atk, f"{self._protecting_move}で防がれた"))
    battle.logger.append(TurnLog(battle.turn, dfn, f"{self._protecting_move}成功"))

    return True
