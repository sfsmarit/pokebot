from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Weather
from pokebot.core import Move
from pokebot.logger import TurnLog


def _charge_move(self: TurnManager,
                 idx: PlayerIndex,
                 move: Move) -> bool:

    battle = self.battle
    attacker = battle.pokemon[idx]
    attacker_mgr = battle.poke_mgr[idx]

    if "hide" in move.tags:
        attacker_mgr.hidden = True
    elif move.name in ['メテオビーム', 'エレクトロビーム', 'ロケットずつき']:
        attacker_mgr.activate_move_effect(move)

    if (move.name in ['ソーラービーム', 'ソーラーブレード'] and battle.field_mgr.weather(idx) == Weather.SUNNY) or \
            (move.name == 'エレクトロビーム' and battle.field_mgr.weather(idx) == Weather.RAINY):
        # 溜め省略
        attacker_mgr.unresponsive_turn = 0
        battle.logger.append(TurnLog(battle.turn, idx, '溜め省略'))
    elif attacker.item.name == 'パワフルハーブ' and attacker_mgr.activate_item():
        pass
    else:
        battle.logger.append(TurnLog(battle.turn, idx, '行動不能 溜め'))
        return False

    return True
