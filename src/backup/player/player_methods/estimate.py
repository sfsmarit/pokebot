from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..player import Player

from pokebot.common.enums import MoveCategory
from pokebot.common.constants import NATURE_MODIFIER, STAT_CODES_KANJI
import pokebot.common.utils as ut
from pokebot.model import Pokemon, Item, Move
from pokebot.core.battle import Battle
from pokebot.core.move_utils import effective_move_category


def estimate_attack(self: Player,
                    battle: Battle,
                    poke: Pokemon,
                    stat_idx: int,
                    recursive: bool) -> bool:

    opp = int(not self.idx)
    move_category = MoveCategory.PHY if stat_idx == 1 else MoveCategory.SPE

    errors = []

    # ダメージ履歴を参照する
    for log in battle.logger.damage_logs:
        # 推定に使えないログを除外
        if log.idx != opp or \
                log.pokemons[opp]['_name'] != poke.name or \
                effective_move_category(battle, opp, log.move) != move_category or \
                log.move in ['イカサマ', 'ボディプレス']:
            continue

        if not recursive:
            # 1度目の計算では、ダメージが発生した状況を再現する
            btl = battle.restore_from_damage_log(log)

            # 非公開情報の隠蔽
            if not btl.open_sheet:
                btl.mask(perspective=self.idx)
        else:
            # 2度目以降は渡されたbattleをそのまま使う
            btl = battle

        # ダメージ計算
        single_hit_damages = btl.damage_mgr.single_hit_damages(opp, log.move, critical=log.critical)

        if single_hit_damages[0] > log.damage_dealt:
            # 火力を過大評価
            errors.append(+1)
        elif single_hit_damages[-1] < log.damage_dealt:
            # 火力を過小評価
            errors.append(-1)
        else:
            # 誤差なし
            errors.append(0)

    # 推定材料がなければ中止
    if not errors:
        return False

    # 観測値と矛盾がなければ終了
    if not any(errors):
        return True

    # 評価結果に一貫性がなければ中止
    if +1 in errors and -1 in errors:
        # print(f"{PokeDB.stats_kanji[stat_idx]}を推定できません")
        return False

    if recursive:
        return False

    # 探索候補 (低火力順)
    # 0
    # 252
    # +252
    # こだわり252
    # こだわり+252

    pc = btl.pokemons[opp]

    # 性格
    nn = pc.nature if NATURE_MODIFIER[pc.nature][stat_idx] == 1 else 'まじめ'
    nu = 'いじっぱり' if move_category == MoveCategory.PHY else 'ひかえめ'
    natures = [nn, nn, nu]

    # 努力値
    efforts = [0, 252, 252]

    # アイテム
    items = [pc.item]*3

    # アイテムが観測されていなければ、探索条件を追加する
    if not pc.item.observed:
        if 'こだわり' not in ''.join(pc.rejected_item_names):
            natures += [nn, nu]
            efforts += [252, 252]
            items += [Item('こだわりハチマキ' if move_category == MoveCategory.PHY else 'こだわりメガネ')]*2

    # 火力を過大評価しているなら、探索順を逆にする
    if +1 in errors:
        natures.reverse()
        efforts.reverse()
        items.reverse()

    # 現状の火力指数を計算
    eff_stats = pc.stats[stat_idx]

    match pc.item.name:
        case 'こだわりハチマキ':
            if move_category == MoveCategory.PHY:
                eff_stats *= pc.item.power_correction
        case 'こだわりメガネ':
            if move_category == MoveCategory.SPE:
                eff_stats *= pc.item.power_correction

    # 探索
    for nature, effort, item in zip(natures, efforts, items):
        pc.nature = nature
        pc.set_effort(stat_idx, effort)
        pc.item = item

        st = pc.stats[stat_idx]

        match item.name:
            case 'こだわりハチマキ':
                if move_category == MoveCategory.PHY:
                    st *= item.power_correction
            case 'こだわりメガネ':
                if move_category == MoveCategory.SPE:
                    st *= item.power_correction

        if +1 in errors:
            # 火力を過大評価していれば、現状以上の火力指数は検証しない
            if st > eff_stats:
                continue
        else:
            # 火力を過小評価していれば、現状以下の火力指数は検証しない
            if st < eff_stats:
                continue

        # 探索条件がダメージ履歴に合致すれば、元のポケモンを更新する
        if estimate_attack(self, btl, pc, stat_idx, recursive=True):
            poke.nature = nature
            poke.set_effort(stat_idx, effort)
            poke.item = item
            return True

    return False


def estimate_defence(self: Player,
                     battle: Battle,
                     poke: Pokemon,
                     stat_idx: int,
                     recursive: bool) -> bool:
    opp = int(not self.idx)
    move_category = MoveCategory.PHY if stat_idx == 2 else MoveCategory.SPE

    errors = []

    # ダメージ履歴を参照する
    for log in battle.logger.damage_logs:
        # 推定に使えない条件
        if log.idx == opp or \
                log.pokemons[opp]['_name'] != poke.name or \
                effective_move_category(battle, self.idx, log.move) != move_category or \
                (stat_idx != 2 and "physical" in Move(log.move).tags):
            continue

        if not recursive:
            # 1度目の計算では、ダメージが発生した状況を再現する
            btl = battle.restore_from_damage_log(log)

            # 非公開情報の隠蔽
            if not btl.open_sheet:
                btl.mask(perspective=self.idx)
        else:
            # 2度目以降は渡されたbattleをそのまま使う
            btl = battle

        # 非公開情報の削除
        if not recursive and not btl.open_sheet:
            btl.pokemons[opp].mask()

        # 推定されるダメージ
        single_hit_damages = btl.damage_mgr.single_hit_damages(self.idx, log.move, critical=log.critical)
        damage_ratios = [round(d/btl.pokemons[opp].stats[0], 2) for d in single_hit_damages]

        if damage_ratios[0] > log.damage_ratio:
            # 推定ダメージが過大 = 耐久を過小評価
            errors.append(-1)
        elif damage_ratios[-1] < log.damage_ratio:
            # 推定ダメージが過小 = 耐久を過大評価
            errors.append(+1)
        else:
            errors.append(0)

    # 該当するダメージ履歴なし
    if not errors:
        return False

    # 観測値と矛盾がなければ終了
    if not any(errors):
        return True

    # 評価結果に一貫性がなければ中止
    if +1 in errors and -1 in errors:
        # print(f"{STAT_CODES_KANJI[stat_idx]}を推定できません")
        return False

    if recursive:
        return False

    # 探索範囲 (低->高耐久)
    # 0
    # H252
    # B/D252
    # HB/D252
    # HB/D+252
    # H252 とつげきチョッキ
    # HD252 とつげきチョッキ

    pc = btl.pokemons[opp]

    # 性格
    nn = pc.nature if NATURE_MODIFIER[pc.nature][stat_idx] == 1 else 'まじめ'
    if NATURE_MODIFIER[pc.nature][1] == 0.9:
        nu = 'ずぶとい' if move_category == MoveCategory.PHY else 'おだやか'
    elif NATURE_MODIFIER[pc.nature][3] == 0.9:
        nu = 'わんぱく' if move_category == MoveCategory.PHY else 'しんちょう'
    else:
        nu = 'のんき' if move_category == MoveCategory.PHY else 'なまいき'

    natures = [nn, nn, nn, nn, nu]

    # 努力値
    efforts_H = [0, 252, 0, 252, 252]
    efforts = [0, 0, 252, 252, 252]

    # アイテム
    items = [pc.item]*5

    # アイテムが観測されていなければ、探索条件を追加する
    if not pc.item.observed:
        if move_category == MoveCategory.SPE and 'とつげきチョッキ' not in pc.rejected_item_names:
            natures += [nn, nu]
            efforts += [252, 252]
            items += [Item('とつげきチョッキ')]*2

    # 耐久を過大評価しているなら探索順を逆にする
    if +1 in errors:
        natures.reverse()
        efforts_H.reverse()
        efforts.reverse()
        items.reverse()

    # 現状の耐久指数を計算
    eff_stats = pc.stats[0] * pc.stats[stat_idx]

    match pc.item.name:
        case 'とつげきチョッキ':
            if move_category == MoveCategory.SPE:
                eff_stats *= 1.5

    # 探索
    for nature, effort, effort_H, item in zip(natures, efforts, efforts_H, items):
        pc.nature = nature
        pc.set_effort(stat_idx, effort)
        pc.set_effort(0, effort_H)
        pc.item = item

        st = pc.stats[0] * pc.stats[stat_idx]

        match item.name:
            case 'とつげきチョッキ':
                if move_category == MoveCategory.SPE:
                    st *= 1.5

        if +1 in errors:
            # 耐久を過大評価していれば、現状以上の耐久指数は検証しない
            if st > eff_stats:
                continue
        else:
            # 耐久を過小評価していれば、現状以下の耐久指数は検証しない
            if st < eff_stats:
                continue

        # 探索条件がダメージ履歴に整合すればポケモンを更新する
        if estimate_defence(self, btl, pc, stat_idx, recursive=True):
            poke.nature = nature
            poke.set_effort(stat_idx, effort)
            poke.set_effort(0, effort_H)
            poke.item = item
            return True

    return False


def estimate_speed(poke: Pokemon) -> bool:
    """speed_rangeからステータスと持ち物を推定する"""
    if poke.speed_range[0] <= poke.stats[5] <= poke.speed_range[1]:
        return True

    v = poke.speed_range[0] if poke.stats[5] < poke.speed_range[0] else poke.speed_range[1]

    # スカーフ判定
    if v > Pokemon.calc_stats(poke.name, 'ようき', efforts=[0]*5+[252])[5]:
        poke.item = 'こだわりスカーフ'
        v = ut.round_half_up(v/1.5)

    # 努力値推定
    ac = [poke.stats[1], poke.stats[3]]
    if ac.index(max(ac)) == 0:
        natures = ['ようき', 'いじっぱり', 'ゆうかん', 'まじめ']
    else:
        natures = ['おくびょう', 'ひかえめ', 'れいせい', 'まじめ']

    efforts_50 = [0] + [4+8*i for i in range(32)]
    efforts_50.reverse()

    for nature in natures:
        a = [Pokemon.calc_stats(poke.name, nature, efforts=[0]*5+[eff])[5]
             for eff in efforts_50]
        for i in range(len(a[:-1])):
            if a[i+1] <= v <= a[i]:
                poke.nature = nature
                poke.set_stats(5, a[i])
                return True

    return False
