from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import MoveCategory
from pokebot.pokedb import Move
from pokebot.logger import TurnLog, DamageLog


def _process_special_damage(self: TurnManager,
                            atk: PlayerIndex | int,
                            move: Move):
    """ダメージ計算式に従わない技のダメージを計算する"""
    dfn = int(not atk)
    attacker = self.battle.pokemons[atk]
    defender = self.battle.pokemons[dfn]
    defender_mgr = self.battle.poke_mgrs[dfn]

    # ログ生成
    self.battle.damage_mgr.log = DamageLog(self.battle, atk, move)

    if self.battle.damage_mgr.defence_type_modifier(atk, move) == 0 or \
            self.battle.damage_mgr.damage_modifier(atk, move) == 0:
        return False

    match move.name:
        case 'いかりのまえば' | 'カタストロフィ':
            self.damage_dealt[atk] = int(defender.hp/2)
        case 'カウンター' | 'ミラーコート':
            move_category = MoveCategory.PHY if move.name == 'カウンター' else MoveCategory.SPE
            if defender_mgr.executed_move.category == move_category:
                self.damage_dealt[atk] = int(self.damage_dealt[dfn]*2)
        case 'ほうふく' | 'メタルバースト':
            self.damage_dealt[atk] = int(self.damage_dealt[dfn]*1.5)
        case 'ちきゅうなげ' | 'ナイトヘッド':
            self.damage_dealt[atk] = attacker.level
        case 'いのちがけ':
            self.damage_dealt[atk] = attacker.hp
            attacker.hp = 0
            self.battle.logger.append(TurnLog(self.battle.turn, atk, "瀕死"))
        case 'がむしゃら':
            self.damage_dealt[atk] = max(0, defender.hp - attacker.hp)
        case _:
            if "one_ko" in move.tags and \
                    defender_mgr.defending_ability(move).name != 'がんじょう' and \
                    not (move.name == 'ぜったいれいど' and 'こおり' in defender_mgr.types):
                self.damage_dealt[atk] = defender.hp


def _modify_damage(self: TurnManager, atk: PlayerIndex | int):
    dfn = int(not atk)
    defender = self.battle.pokemons[dfn]
    defender_mgr = self.battle.poke_mgrs[dfn]

    # ダメージ上限 = 残りHP
    self.damage_dealt[atk] = min(defender.hp, self.damage_dealt[atk])

    # ダメージ修正
    if self._koraeru and self.damage_dealt[atk] == defender.hp:
        # こらえる
        self.damage_dealt[atk] -= 1
        self.move_succeeded[dfn] = True
    elif defender_mgr.defending_ability(self.move[atk]).name == 'がんじょう' and \
            defender_mgr.activate_ability():
        pass
    elif defender.item.name in ['きあいのタスキ', 'きあいのハチマキ']:
        defender_mgr.activate_item()
