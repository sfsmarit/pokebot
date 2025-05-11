from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import MoveCategory
from pokebot.core import Move
from pokebot.logger import TurnLog, DamageLog


def _process_special_damage(self: TurnManager,
                            atk: PlayerIndex,
                            move: Move):
    """ダメージ計算式に従わない技のダメージを計算する"""
    battle = self.battle

    dfn = PlayerIndex(not atk)
    attacker = battle.pokemon[atk]
    defender = battle.pokemon[dfn]
    attacker_mgr = battle.poke_mgr[atk]
    defender_mgr = battle.poke_mgr[dfn]

    # ログ生成
    battle.damage_mgr.log = DamageLog(battle, atk, move)

    if battle.damage_mgr.defence_type_modifier(atk, move) == 0 or \
            battle.damage_mgr.damage_modifier(atk, move) == 0:
        return False

    match move.name:
        case 'ぜったいれいど' | 'じわれ' | 'つのドリル' | 'ハサミギロチン':
            if defender_mgr.defending_ability(move) != 'がんじょう' or \
                    not (move.name == 'ぜったいれいど' and 'こおり' in defender_mgr.types):
                self.damage_dealt[atk] = defender.hp
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
            battle.logger.append(TurnLog(battle.turn, atk, f"いのちがけ {-self.damage_dealt[atk]}"))
        case 'がむしゃら':
            self.damage_dealt[atk] = max(0, defender.hp - attacker.hp)


def _modify_damage(self: TurnManager, atk: PlayerIndex):
    battle = self.battle

    dfn = PlayerIndex(not atk)
    defender = battle.pokemon[dfn]
    defender_mgr = battle.poke_mgr[dfn]

    # ダメージ上限 = 残りHP
    self.damage_dealt[atk] = min(defender.hp, self.damage_dealt[atk])

    # ダメージ修正
    if self._koraeru and self.damage_dealt[atk] == defender.hp:
        # こらえる
        self.damage_dealt[atk] -= 1
        self.move_succeeded[dfn] = True
    elif defender.ability.name == 'がんじょう' and \
            defender_mgr.activate_ability():
        pass
    elif defender.item in ['きあいのタスキ', 'きあいのハチマキ']:
        defender_mgr.activate_item()
