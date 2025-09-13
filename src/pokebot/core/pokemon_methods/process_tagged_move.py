from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..pokemon_manager import ActivePokemonManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Condition, SideField
from pokebot.model import Move
from pokebot.logger import TurnLog


def _process_tagged_move(self: ActivePokemonManager,
                         move: Move,
                         tag: str) -> bool:

    if tag not in move.tags:
        return False

    dfn = int(not self.idx)
    attacker = self.pokemon
    defender_mgr = self.battle.poke_mgrs[dfn]

    match tag:
        case 'bind':
            # バインド技
            count = 7 if attacker.item.name == 'ねばりのかぎづめ' else 5
            if not self.battle.turn_mgr._hit_substitute and \
                    defender_mgr.set_condition(Condition.BIND, count):
                defender_mgr.bind_damage_denom = 6 if attacker.item.name == 'しめつけバンド' else 8
                return True

        case 'immovable':
            # 反動で行動できない技
            self.forced_turn = 1
            return True

        case 'rage':
            if self.forced_turn == 0:
                # あばれる状態の付与
                self.forced_turn = self.battle.random.randint(1, 2)
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{move} 残り{self.forced_turn}ターン"))
            else:
                # ターン経過
                self.forced_turn -= 1
                # こんらん付与
                if self.set_condition(Condition.CONFUSION, self.battle.random.randint(2, 5)):
                    self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{move}解除 こんらん"))
            return True

        case 'wall_break':
            # 壁破壊
            if self.battle.turn_mgr.damage_dealt[self.idx]:
                broken = self.battle.field_mgr.set_field(SideField.REFLECTOR, dfn, 0)
                broken |= self.battle.field_mgr.set_field(SideField.LIGHT_WALL, dfn, 0)
                if broken:
                    self.battle.logger.append(TurnLog(self.battle.turn, self.idx, '壁破壊'))
                    return True

    return False
