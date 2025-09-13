from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..pokemon_manager import ActivePokemonManager

from pokebot.common.enums import Ailment, MoveCategory, Condition, \
    BoostSource, GlobalField
from pokebot.common.constants import FIELD_SEED, STAT_CODES
from pokebot.model import Move
from pokebot.logger import TurnLog


def _activate_item(self: ActivePokemonManager,
                   move: Move | None) -> bool:
    battle = self.battle

    opp = int(not self.idx)
    opponent_mgr = battle.poke_mgrs[opp]

    if not self.pokemon.item.active:
        return False

    r_berry = 2 if self.pokemon.ability.name == 'じゅくせい' else 1
    activated = False

    # 瀕死でも発動するアイテム
    match self.pokemon.item.name:
        case 'ゴツゴツメット':
            activated = move and \
                not battle.turn_mgr._hit_substitute and \
                opponent_mgr.contacts(move) and \
                opponent_mgr.add_hp(ratio=-1/6)
        case 'ふうせん':
            activated = True
        case 'ジャポのみ' | 'レンブのみ':
            move_category = {"ジャポのみ": MoveCategory.PHY,
                             "レンブのみ": MoveCategory.SPE}
            activated = move and \
                move.category == move_category[self.pokemon.item.name] and \
                not self.is_nervous() and \
                opponent_mgr.add_hp(ratio=-r_berry/8)

    # 瀕死でないならば発動するアイテム
    match self.pokemon.item.name * (self.pokemon.hp > 0):
        case 'いのちのたま':
            activated = self.add_hp(ratio=-0.1)
        case 'かいがらのすず':
            activated = self.add_hp(int(battle.turn_mgr.damage_dealt[self.idx]/8))
        case 'かえんだま':
            activated = self.set_ailment(Ailment.BRN, ignore_shinpi=True)
        case 'どくどくだま':
            activated = self.set_ailment(Ailment.PSN, bad_poison=True, ignore_shinpi=True)
        case 'エレキシード' | 'グラスシード' | 'サイコシード' | 'ミストシード':
            if self.pokemon.item.name in ['エレキシード', 'グラスシード']:
                stat_idx = 2
            else:
                stat_idx = 4
            activated = self.pokemon.item.name == FIELD_SEED[battle.field_mgr.terrain(self.idx)] and \
                self.add_rank(stat_idx, +1)
        case 'おうじゃのしるし' | 'するどいキバ':
            r = 2 if self.pokemon.ability.name == 'てんのめぐみ' else 1
            activated = battle.random.random() < 0.1 * r
            if activated:
                battle.turn_mgr._flinch = True
        case 'からぶりほけん':
            activated = move and \
                "one_ko" not in move.tags and \
                self.add_rank(5, +2)
        case 'きあいのタスキ':
            activated = battle.turn_mgr.damage_dealt[opp] == self.pokemon.stats[0]
            if activated:
                battle.turn_mgr.damage_dealt[opp] -= 1
        case 'きあいのハチマキ':
            activated = battle.turn_mgr.damage_dealt[opp] == self.pokemon.hp
            if activated:
                battle.turn_mgr.damage_dealt[opp] -= 1
        case 'きゅうこん' | 'ひかりごけ':
            activated = move and \
                move.type == 'みず' and \
                not battle.turn_mgr._hit_substitute and \
                self.add_rank(3, +1)
        case 'じゅうでんち' | 'ゆきだま':
            t = 'でんき' if self.pokemon.item.name == 'じゅうでんち' else 'こおり'
            activated = move and \
                move.type == t and \
                not battle.turn_mgr._hit_substitute and \
                self.add_rank(1, +1)
        case 'たべのこし' | 'くろいヘドロ':
            if self.pokemon.item.name == 'くろいヘドロ' and 'どく' not in self.types:
                sign = -1
            else:
                sign = 1
            activated = self.add_hp(ratio=sign/16)
        case 'じゃくてんほけん':
            activated = move and \
                not battle.turn_mgr._hit_substitute and \
                battle.damage_mgr.defence_type_modifier(self.idx, move) > 1 and \
                self.add_rank(values=[0, 2, 0, 2])
        case 'しろいハーブ':
            activated = any([v < 0 for v in self.rank])
            if activated:
                self.rank = [max(0, v) for v in self.rank]
        case 'せんせいのツメ':
            activated = battle.random.random() < 0.2
        case 'だっしゅつボタン':
            activated = battle.turn_mgr.damage_dealt[opp] and \
                battle.switchable_indexes(self.idx)
        case 'のどスプレー':
            activated = move and \
                "sound" in move.tags and \
                self.add_rank(3, +1)
        case 'パワフルハーブ':
            activated = self.forced_turn > 0
            if activated:
                self.forced_turn = 0
                battle.logger.append(TurnLog(battle.turn, self.idx, '溜め省略'))
        case 'ブーストエナジー':
            activated = self.boost_source == BoostSource.NONE
            if activated:
                self.boost_source = BoostSource.ITEM
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx,
                                                  f"{STAT_CODES[self.boosted_idx]}上昇"))  # type: ignore

        case 'メンタルハーブ':
            for cond in [Condition.MEROMERO, Condition.ENCORE,
                         Condition.KANASHIBARI, Condition.CHOHATSU, Condition.HEAL_BLOCK]:
                activated = self.set_condition(cond, 0)
                if activated:
                    break
        case 'ものまねハーブ':
            activated = True
        case 'ルームサービス':
            activated = battle.field_mgr.count[GlobalField.TRICKROOM] and \
                self.add_rank(5, -1)
        case 'レッドカード':
            activated = opponent_mgr.is_blowable()
            if activated:
                switch_idx = battle.random.choice(battle.switchable_indexes(opp))
                battle.turn_mgr.switch_pokemon(opp, switch_idx=switch_idx)

    if self.pokemon.ability.name == 'くいしんぼう':
        hp_ratio_threshold = 0.5
    else:
        hp_ratio_threshold = 0.25

    match self.pokemon.item.name * (not self.is_nervous()):
        case 'イバンのみ':
            activated = self.pokemon.hp_ratio <= hp_ratio_threshold
        case 'オレンのみ':
            activated = self.pokemon.hp_ratio <= hp_ratio_threshold and \
                not self.count[Condition.HEAL_BLOCK] and \
                self.add_hp(10*r_berry)
        case 'オボンのみ' | 'ナゾのみ':
            if self.pokemon.item.name == 'オボンのみ':
                activated = self.pokemon.hp_ratio <= 0.5
            else:
                activated = move is not None and \
                    battle.damage_mgr.defence_type_modifier(self.idx, move) > 1
            activated = activated and \
                not self.count[Condition.HEAL_BLOCK] and \
                self.add_hp(ratio=0.25*r_berry)
        case 'フィラのみ' | 'ウイのみ' | 'マゴのみ' | 'バンジのみ' | 'イアのみ':
            activated = not self.count[Condition.HEAL_BLOCK] and \
                self.add_hp(ratio=r_berry/3)
        case 'ヒメリのみ':
            for move in self.pokemon.moves:
                if move.pp == 0:
                    move.add_pp(10)
                    activated = True
                    break
        case 'カゴのみ':
            activated = self.pokemon.ailment == Ailment.SLP and \
                self.set_ailment(Ailment.NONE)
        case 'クラボのみ':
            activated = self.pokemon.ailment == Ailment.PAR and \
                self.set_ailment(Ailment.NONE)
        case 'チーゴのみ':
            activated = self.pokemon.ailment == Ailment.BRN and \
                self.set_ailment(Ailment.NONE)
        case 'ナナシのみ':
            activated = self.pokemon.ailment == Ailment.FLZ and \
                self.set_ailment(Ailment.NONE)
        case 'モモンのみ':
            activated = self.pokemon.ailment == Ailment.PSN and \
                self.set_ailment(Ailment.NONE)
        case 'ラムのみ':
            activated = self.pokemon.ailment.value and \
                self.set_ailment(Ailment.NONE)
        case 'キーのみ':
            activated = self.set_condition(Condition.CONFUSION, 0)
        case 'チイラのみ':
            activated = self.pokemon.hp_ratio <= hp_ratio_threshold and \
                self.add_rank(1, r_berry)
        case 'リュガのみ' | 'アッキのみ':
            activated = self.pokemon.hp_ratio <= hp_ratio_threshold and \
                self.add_rank(2, r_berry)
        case 'ヤタピのみ':
            activated = self.pokemon.hp_ratio <= hp_ratio_threshold and \
                self.add_rank(3, r_berry)
        case 'ズアのみ' | 'タラプのみ':
            activated = self.pokemon.hp_ratio <= hp_ratio_threshold and \
                self.add_rank(4, r_berry)
        case 'カムラのみ':
            activated = self.pokemon.hp_ratio <= hp_ratio_threshold and \
                self.add_rank(5, r_berry)
        case 'サンのみ':
            activated = self.set_condition(Condition.CRITICAL, 2)
        case 'スターのみ':
            stat_idx = battle.random.choice([i for i in range(1, 6) if self.rank[i] < 6])
            activated = self.add_rank(stat_idx, r_berry)
        case 'アッキのみ':
            activated = move and move.category == MoveCategory.PHY and \
                self.add_rank(2, +1)
        case 'タラプのみ':
            activated = move and move.category == MoveCategory.SPE and \
                self.add_rank(4, +1)

    if not activated:
        return False

    # きのみ関連の特性の発動
    if self.pokemon.item.name[-2:] == 'のみ' and \
            "berry" in self.pokemon.ability.tags:
        self.activate_ability()

    # アイテム消費
    if self.pokemon.item.consumable:
        self.pokemon.item.consume()
        battle.logger.append(TurnLog(battle.turn, self.idx, f"{self.pokemon.item.name_lost}消費"))
        if self.pokemon.ability.name == 'かるわざ':
            self.activate_ability()
    else:
        battle.logger.append(TurnLog(battle.turn, self.idx, f"{self.pokemon.item.name}発動"))
        self.pokemon.item.observed = True  # 観測

    return True
