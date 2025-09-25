from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..damage_manager import DamageManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Ailment, Condition, Weather, Terrain
from pokebot.common.constants import HEAL_BERRIES
from pokebot.pokedb import Move
from pokebot.core.move_utils import num_strikes

from . import lethal_utils as lut


def lethal(self: DamageManager,
           atk: PlayerIndex | int,
           move_list: list[Move | str],
           combo_hits: int | None,
           max_loop: int):
    """
    致死率計算

    Parameters
    ----------
    battle: Battle
        Battleインスタンス
    atk_idx: int
        攻撃側のプレイヤー番号
    move_list: [str]
        攻撃技. 2個以上の場合は加算ダメージを計算
    combo_hits: int
        連続技の回数
    max_loop: int
        加算ループの上限回数

    Returns
    ----------
    str
        "d1~d2 (p1~p2 %) 確n" 形式の文字列.
    """

    dfn = int(not atk)
    defender = self.battle.pokemons[dfn]
    attacker_mgr = self.battle.poke_mgrs[atk]
    defender_mgr = self.battle.poke_mgrs[dfn]

    move_names, damage_dist_list = [], []

    # 単発ダメージ計算
    for move in move_list:
        if isinstance(move, str):
            move = Move(move)

        n_strikes = num_strikes(self.battle, atk, move, n_default=combo_hits)

        for i in range(n_strikes):
            # 1ヒットあたりのダメージを計算
            critical = "critical" in move.tags
            r_power = i+1 if move.name == 'トリプルアクセル' else 1

            single_hit_damages = self.single_hit_damages(
                atk, move, critical=critical, power_multiplier=r_power, lethal_calc=True,)

            if not single_hit_damages:
                break

            move_names.append(move.name)

            dstr = {}
            for v in single_hit_damages:
                lut.push(dstr, str(v), 1)

            damage_dist_list.append(dstr)

        # ターン終了フラグを追加
        move_names.append('END')
        damage_dist_list.append({})

    if not move_names:
        return

    # 初期化
    self.damage_dstr = {'0': 1}
    self.hp_dstr = {str(defender.hp): 1}
    self.lethal_num = 0
    self.lethal_prob = 0

    can_heal = defender.item.name in HEAL_BERRIES and not defender_mgr.is_nervous()

    # {残りHP: 場合の数}
    hp_dstr = {str(defender.hp)+('.0' if defender.item.active else ''): 1}

    # 瀕死になるまでターンを進める
    for i in range(max_loop):
        self.lethal_num += 1

        # 加算計算
        for (mv, damage_dstr) in zip(move_names, damage_dist_list):
            if mv != 'END':
                # ダメージ計算
                move = Move(mv)
                new_hp_dstr, new_damage_dstr = {}, {}

                for hp in hp_dstr:
                    for dmg in damage_dstr:
                        # ダメージ修正
                        d = int(dmg)
                        if float(hp) == defender.stats[0] and \
                                defender_mgr.defending_ability(move) in ['ファントムガード', 'マルチスケイル']:
                            d = int(d/2)

                        # HPからダメージを引く
                        hp_key = str(int(max(0, float(hp)-d))) + '.0'*(hp[-2:] == '.0')

                        lut.push(new_hp_dstr, hp_key, hp_dstr[hp]*damage_dstr[dmg])
                        lut.push(new_damage_dstr, str(d), hp_dstr[hp]*damage_dstr[dmg])

                hp_dstr = new_hp_dstr.copy()

                if can_heal:
                    hp_dstr = lut.apply_berry_heal(defender, hp_dstr)

                # 1セット目の合計ダメージを記録
                if i == 0:
                    cross_sum = {}
                    for k1, v1 in self.damage_dstr.items():
                        for k2, v2 in new_damage_dstr.items():
                            cross_sum[str(int(k1)+int(k2))] = v1 * v2
                    self.damage_dstr = cross_sum

                    for key, value in self.damage_dstr.items():
                        new_key = str(int(key) / defender.stats[0])
                        self.damage_ratio_dstr[new_key] = value

            else:
                # ターン終了時の処理
                # 砂嵐ダメージ
                if self.battle.field_mgr.weather() == Weather.SAND and \
                    not defender_mgr.is_overcoat() and \
                    all(s not in defender_mgr.types for s in ['いわ', 'じめん', 'はがね']) and \
                        defender.ability.name not in ['すなかき', 'すながくれ', 'すなのちから', 'マジックガード']:  # type: ignore
                    hp_dstr = lut.offset_hp(hp_dstr, -int(defender.stats[0]/16))

                    if can_heal:
                        hp_dstr = lut.apply_berry_heal(defender, hp_dstr)

                # 天候に関する特性
                match self.battle.field_mgr.weather(dfn):
                    case Weather.SUNNY:
                        if defender.ability.name in ['かんそうはだ', 'サンパワー']:  # type: ignore
                            hp_dstr = lut.offset_hp(hp_dstr, -int(defender.stats[0]/8))

                            if can_heal:
                                hp_dstr = lut.apply_berry_heal(defender, hp_dstr)
                    case Weather.RAINY:
                        match defender.ability.name:  # type: ignore
                            case 'あめうけざら':
                                hp_dstr = lut.offset_hp(hp_dstr, int(defender.stats[0]/16))
                            case 'かんそうはだ':
                                hp_dstr = lut.offset_hp(hp_dstr, int(defender.stats[0]/8))
                    case Weather.SNOW:
                        if defender.ability.name == 'アイスボディ':
                            hp_dstr = lut.offset_hp(hp_dstr, int(defender.stats[0]/16))

                # グラスフィールド
                if self.battle.field_mgr.terrain(dfn) == Terrain.GRASS:
                    hp_dstr = lut.offset_hp(hp_dstr, int(defender.stats[0]/16))

                # たべのこし系
                match defender.item.name:
                    case 'たべのこし':
                        hp_dstr = lut.offset_hp(hp_dstr, int(defender.stats[0]/16))
                    case 'くろいヘドロ':
                        r = 1 if 'どく' in defender_mgr.types else -1*(defender.ability.name != 'マジックガード')
                        hp_dstr = lut.offset_hp(hp_dstr, int(defender.stats[0]/16*r))
                        if r == -1 and can_heal:
                            hp_dstr = lut.apply_berry_heal(defender, hp_dstr)

                # アクアリング・ねをはる
                h = attacker_mgr.hp_drain_amount(int(defender.stats[0]/16), from_opponent=False)
                if defender_mgr.count[Condition.AQUA_RING]:
                    hp_dstr = lut.offset_hp(hp_dstr, h)
                if defender_mgr.count[Condition.NEOHARU]:
                    hp_dstr = lut.offset_hp(hp_dstr, h)

                # やどりぎのタネ
                if defender_mgr.count[Condition.YADORIGI] and defender.ability.name != 'マジックガード':
                    hp_dstr = lut.offset_hp(hp_dstr, -int(defender.stats[0]/16))
                    if can_heal:
                        hp_dstr = lut.apply_berry_heal(defender, hp_dstr)

                # 状態異常ダメージ
                if defender.ability.name != 'マジックガード':
                    h = 0

                    match defender.ailment:
                        case Ailment.PSN:
                            if defender.ability.name == 'ポイズンヒール':
                                h = int(defender.stats[0]/8)
                            elif defender_mgr.count[Condition.BAD_POISON]:
                                h = -int(defender.stats[0]/16 * defender_mgr.count[Condition.BAD_POISON])
                                defender_mgr.count[Condition.BAD_POISON] += 1
                            else:
                                h = -int(defender.stats[0]/8)
                        case Ailment.BRN:
                            h = -int(defender.stats[0]/16)

                    if h:
                        hp_dstr = lut.offset_hp(hp_dstr, h)

                        if h < 0 and can_heal:
                            hp_dstr = lut.apply_berry_heal(defender, hp_dstr)

                # 呪いダメージ
                if defender_mgr.count[Condition.NOROI] and defender.ability.name != 'マジックガード':
                    hp_dstr = lut.offset_hp(hp_dstr, -int(defender.stats[0]/4))

                    if can_heal:
                        hp_dstr = lut.apply_berry_heal(defender, hp_dstr)

                # バインドダメージ
                if defender_mgr.count[Condition.BIND] and defender.ability.name != 'マジックガード':
                    hp_dstr = lut.offset_hp(hp_dstr,
                                            -int(defender.stats[0]/10/defender_mgr.bind_damage_denom))
                    if can_heal:
                        hp_dstr = lut.apply_berry_heal(defender, hp_dstr)

                # しおづけダメージ
                if defender_mgr.count[Condition.SHIOZUKE] and defender.ability.name != 'マジックガード':
                    r = 1
                    if any(t in defender_mgr.types for t in ['みず', 'はがね']):
                        r *= 2
                    hp_dstr = lut.offset_hp(hp_dstr, -int(defender.stats[0]/8*r))
                    if can_heal:
                        hp_dstr = lut.apply_berry_heal(defender, hp_dstr)

                # 1ターン目のHPを記録
                if i == 0:
                    self.hp_dstr = hp_dstr.copy()

                # 致死率を計算
                self.lethal_prob = lut.zero_ratio(hp_dstr)

                # 瀕死判定
                if self.lethal_prob:
                    break

        # 瀕死判定
        if self.lethal_prob:
            break
