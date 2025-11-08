from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..active_pokemon_manager import ActivePokemonManager

from pokebot.common.enums import Ailment, Condition, SideField, Terrain
import pokebot.common.utils as ut
from pokebot.model import Move
from pokebot.logger import TurnLog


def _activate_move_effect(self: ActivePokemonManager,
                          move: Move) -> bool:

    dfn = int(not self.idx)
    attacker = self.pokemon
    defender = self.opponent
    defender_mgr = self.battle.poke_mgrs[dfn]

    # 追加効果 (相手に付与)
    match move.name * defender_mgr.can_receive_move_effect(move):
        case 'アンカーショット' | 'かげぬい' | 'サウザンウェーブ':
            return defender_mgr.set_condition(Condition.SWITCH_BLOCK, 1)
        case 'うたかたのアリア':
            if defender.ailment == Ailment.BRN:
                defender_mgr.set_ailment(Ailment.NONE)
                self.battle.logger.add(TurnLog(self.battle.turn, self.idx, '追加効果 やけど解除'))
                return True
        case 'ぶきみなじゅもん':
            if defender_mgr.expended_moves and (move := defender_mgr.expended_moves[-1]).pp:
                move.add_pp(-3)
                self.battle.logger.add(TurnLog(self.battle.turn, self.idx, f"追加効果 {move} PP-3"))
                return True
        case 'うちおとす' | 'サウザンアロー':
            if defender_mgr.is_floating():
                defender_mgr.set_condition(Condition.GROUNDED, 1)
                return True
        case 'エレクトロビーム' | 'メテオビーム':
            if self.add_rank(3, +1):
                return True
        case 'ロケットずつき':
            if self.add_rank(2, +1):
                return True
        case 'きつけ':
            if defender.ailment == Ailment.PAR:
                defender_mgr.set_ailment(Ailment.NONE, move)
                self.battle.logger.add(TurnLog(self.battle.turn, dfn, '追加効果 まひ解除'))
                return True
        case 'くらいつく':
            return self.set_condition(Condition.SWITCH_BLOCK, 1) and \
                defender_mgr.set_condition(Condition.SWITCH_BLOCK, 1)
        case 'サイコノイズ':
            return defender_mgr.set_condition(Condition.HEAL_BLOCK, 2)
        case 'しおづけ':
            return defender_mgr.set_condition(Condition.SHIOZUKE, 1)
        case 'じごくづき':
            return defender_mgr.set_condition(Condition.JIGOKUZUKI, 2)
        case 'なげつける':
            match attacker.item.name:
                case 'おうじゃのしるし' | 'するどいキバ':
                    self.battle.turn_mgr._flinch = defender_mgr.can_be_flinched()
                    if self.battle.turn_mgr._flinch:
                        self.battle.logger.add(TurnLog(self.battle.turn, self.idx, '追加効果 ひるみ'))
                case 'かえんだま':
                    if defender_mgr.set_ailment(Ailment.BRN, move):
                        self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, '追加効果'))
                case 'でんきだま':
                    if defender_mgr.set_ailment(Ailment.PAR, move):
                        self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, '追加効果'))
                case 'どくバリ':
                    if defender_mgr.set_ailment(Ailment.PSN, move):
                        self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, '追加効果'))
                case 'どくどくだま':
                    if defender_mgr.set_ailment(Ailment.PSN, move, bad_poison=True):
                        self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, '追加効果'))

            # アイテム消失
            attacker.item.active = False
            attacker.item.observed = True  # 観測
            self.battle.logger.add(TurnLog(self.battle.turn, self.idx, f"{attacker.item.name_lost}消失"))
            return True
        case 'みずあめボム':
            return defender_mgr.set_condition(Condition.AME_MAMIRE, 3)

    # 追加効果/処理 (みがわりにより無効)
    match move.name * (not self.battle.turn_mgr._hit_substitute):
        case 'クリアスモッグ':
            if any(defender_mgr.rank):
                defender_mgr.reset_rank()
                self.battle.logger.add(TurnLog(self.battle.turn, self.idx, '追加効果 能力ランクリセット'))
                return True
        case 'ついばむ' | 'むしくい':
            if defender.item.name[-2:] == 'のみ':
                self.battle.logger.add(TurnLog(self.battle.turn, self.idx, '追加効果'))
                org_item = attacker.item
                attacker.item = defender.item
                self.activate_item()
                attacker.item = org_item
                return True
        case 'ドラゴンテール' | 'ともえなげ':
            if defender_mgr.is_blowable():
                switch_idx = self.battle.random.choice(self.battle.switchable_indexes(dfn))
                self.battle.turn_mgr.switch_pokemon(dfn, switch_idx=switch_idx)
                return True
        case 'どろぼう' | 'ほしがる':
            if not attacker.item.name and defender.item.name and defender_mgr.is_item_removable():
                attacker.item.name = defender.item.name
                attacker.item.observed = True  # 観測
                defender.item.active = False
                self.battle.logger.add(TurnLog(self.battle.turn, self.idx, f"追加効果 {attacker.item}奪取"))
                return True
        case 'はたきおとす':
            if defender.item.name and defender_mgr.is_item_removable():
                defender.item.active = False
                self.battle.logger.add(TurnLog(self.battle.turn, self.idx, f"追加効果 {defender.item.name_lost}消失"))
                return True
        case 'めざましビンタ':
            if defender.ailment == Ailment.SLP:
                defender_mgr.set_ailment(Ailment.NONE)
                self.battle.logger.add(TurnLog(self.battle.turn, self.idx, '追加効果 ねむり解除'))
                return True
        case 'やきつくす':
            if defender.item.name[-2:] == 'のみ' or defender.item.name[-4:] == 'ジュエル':
                defender_mgr.lose_item()
                self.battle.logger.add(TurnLog(self.battle.turn, self.idx, f"追加効果 {defender.item.name_lost}消失"))
                return True

    # 追加効果/処理 (その他)
    match move.name:
        case 'アイアンローラー' | 'アイススピナー':
            if not self.battle.field_mgr.terrain().is_none():
                self.battle.field_mgr.set_terrain(Terrain.NONE, self.idx)
                self.battle.logger.add(TurnLog(self.battle.turn, self.idx, "追加効果 フィールド消失"))
                return True
        case 'おんねん':
            # TODO おんねん実装
            pass
        case 'かえんのまもり':
            if self.set_ailment(Ailment.BRN):
                self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, '追加効果'))
                return True
        case 'スレッドトラップ':
            if self.add_rank(5, -1, by_opponent=True):
                self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, '追加効果'))
                return True
        case 'トーチカ':
            if self.set_ailment(Ailment.PSN):
                self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, '追加効果'))
                return True
        case 'ニードルガード':
            if defender_mgr.add_hp(ratio=-0.125):
                self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, '追加効果'))
                return True
        case 'がんせきアックス':
            if self.battle.field_mgr.add_count(SideField.STEALTH_ROCK, dfn, 1):
                self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, '追加効果'))
                return True
        case 'ひけん・ちえなみ':
            if self.battle.field_mgr.add_count(SideField.MAKIBISHI, dfn, 1):
                self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, '追加効果'))
                return True
        case 'キラースピン' | 'こうそくスピン':
            removed = []
            for field in [Condition.YADORIGI, Condition.BIND]:
                if self.count[field]:
                    self.set_condition(field, 0)
                    removed.append(field)
            for field in [SideField.MAKIBISHI, SideField.DOKUBISHI, SideField.STEALTH_ROCK, SideField.NEBA_NET]:
                if self.battle.field_mgr.set_field(field, self.idx, 0):
                    removed.append(field)
            if removed:
                self.battle.logger.add(TurnLog(self.battle.turn, self.idx, f"追加効果 {[str(field) for field in removed]}解除"))
                return True
        case 'くちばしキャノン':
            pass  # TODO くちばしキャノン実装
        case 'コアパニッシャー':
            if not self.is_first_act() and not defender_mgr.is_ability_protected():
                self.battle.logger.add(TurnLog(self.battle.turn, self.idx, f"追加効果 {defender.ability}消失"))
                defender.ability.active = False
                return True
        case 'スケイルショット':
            if self.add_rank(values=[0, 0, -1, 0, 0, 1]):
                self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, '追加効果'))
                return True
        case 'テラバースト':
            if attacker.terastal == 'ステラ' and attacker.terastal and self.add_rank(values=[0, -1, 0, -1]):
                self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, '追加効果'))
                return True
        case 'でんこうそうげき' | 'もえつきる':
            self.lost_types.append(move.type)
            self.battle.logger.add(TurnLog(self.battle.turn, self.idx, f"追加効果 {move.type}タイプ消失"))
            return True
        case 'とどめばり':
            if defender.hp == 0 and self.add_rank(1, +3):
                self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, '追加効果'))
                return True
        case 'わるあがき':
            self.add_hp(-ut.round_half_up(attacker.stats[0]/4), move=move)
            self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, '反動'))
            return True

    return False
