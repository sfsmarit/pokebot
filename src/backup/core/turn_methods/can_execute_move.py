from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import MoveCategory, Terrain
from pokebot.model import Move
from pokebot.logger import TurnLog


def _can_execute_move(self: TurnManager,
                      idx: PlayerIndex | int,
                      move: Move,
                      tag: str) -> bool:

    dfn = int(not idx)
    attacker = self.battle.pokemons[idx]
    defender = self.battle.pokemons[dfn]
    attacker_mgr = self.battle.poke_mgrs[idx]
    defender_mgr = self.battle.poke_mgrs[dfn]

    moves = self.battle.turn_mgr.move

    # タグ付けされた技の判定
    if tag:
        match tag * (tag in move.tags):
            case 'protect':
                if "protect" in attacker_mgr.executed_move.tags:
                    self.battle.logger.add(TurnLog(self.battle.turn, idx, '連発不可'))
                    return False
            case 'first_turn':
                if attacker_mgr.active_turn:
                    return False

        return True

    match move.name:
        case 'ねごと':
            if not (attacker.is_sleeping() and attacker.get_negoto_moves()):
                return False
        case 'アイアンローラー':
            if self.battle.field_mgr.terrain().is_none():
                return False
        case 'いびき':
            if not attacker.is_sleeping():
                return False
        case 'じばく' | 'だいばくはつ' | 'ビックリヘッド' | 'ミストバースト':
            if 'しめりけ' in (abilities := [p.ability.name for p in self.battle.pokemons]):
                self.battle.pokemons[abilities.index('しめりけ')].ability.observed = True  # 観測
                return False
        case 'じんらい' | 'ふいうち':
            if idx != self.battle.turn_mgr.first_player_idx or \
                    not moves[dfn] or \
                    moves[dfn].category == MoveCategory.STA:  # type: ignore
                return False
        case 'なげつける':
            if not attacker.item.active or \
                    not attacker_mgr.is_item_removable():
                return False
        case 'はやてがえし':
            if idx != self.battle.turn_mgr.first_player_idx or \
                    self.move_speed[dfn] <= 0:
                return False
        case 'ポルターガイスト':
            defender.item.observed = True  # 観測
            if not defender.item.active:
                return False
        case "もえつきる" | "でんこうそうげき":
            if move.type not in attacker_mgr.types:
                return False

    # 特性による先制技無効
    if defender.ability.name in ['じょおうのいげん', 'テイルアーマー', 'ビビッドボディ'] and \
            self.move_speed[idx] >= 1:
        defender.ability.observed = True  # 観測
        self.battle.logger.add(TurnLog(self.battle.turn, idx, defender.ability.name))
        return False

    # サイコフィールドによる先制技無効
    if self.battle.field_mgr.terrain(dfn) == Terrain.PSYCO and \
            self.move_speed[idx] > 0:
        self.battle.logger.add(TurnLog(self.battle.turn, idx, '行動不能 サイコフィールド'))
        return False

    # あくタイプによるいたずらごころ無効
    if attacker.ability.name == 'いたずらごころ' and \
            'あく' in defender_mgr.types and \
            attacker_mgr.expended_moves and \
            attacker_mgr.expended_moves[-1].category == MoveCategory.STA:
        attacker.ability.observed = True  # 観測
        self.battle.logger.add(TurnLog(self.battle.turn, idx, 'いたずらごころ失敗'))
        return False

    return True
