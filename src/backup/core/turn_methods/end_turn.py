from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.enums import Ailment, Weather, Terrain, \
    Condition, GlobalField, SideField
from pokebot.logger import TurnLog


def _end_turn(self: TurnManager):
    """
    ターン終了時の処理を行う。
    """
    battle = self.battle

    # 天候カウント消費
    battle.field_mgr.add_count(GlobalField.WEATHER, v=-1)

    # 砂嵐ダメージ
    if battle.field_mgr.weather() == Weather.SAND:
        for idx in self.speed_order:
            poke = battle.pokemons[idx]
            poke_mgr = battle.poke_mgrs[idx]

            if poke.hp == 0 or \
                    any(s in poke_mgr.types for s in ['いわ', 'じめん', 'はがね']) or \
                    poke.ability.name in ['すなかき', 'すながくれ', 'すなのちから'] or \
                    poke_mgr.is_overcoat() or \
                    (poke_mgr.hidden and poke_mgr.executed_move.name in ['あなをほる', 'ダイビング']):
                continue

            if poke_mgr.add_hp(ratio=-1/16):
                battle.logger.insert(-1, TurnLog(battle.turn, idx, 'すなあらし'))
                if battle.winner() is not None:
                    return

    # 天候に関する特性
    for idx in self.speed_order:
        poke_mgr = battle.poke_mgrs[idx]
        poke = poke_mgr.pokemon

        if poke.hp == 0 or (poke_mgr.hidden and poke_mgr.executed_move.name in ['あなをほる', 'ダイビング']):
            continue

        if poke.ability.name in ['かんそうはだ', 'サンパワー', 'あめうけざら', 'アイスボディ']:
            battle.poke_mgrs[idx].activate_ability()
            if battle.winner() is not None:
                return

    # ねがいごと
    for idx in self.speed_order:
        battle.field_mgr.add_count(SideField.WISH, idx, -1)

    # グラスフィールド回復
    for idx in self.speed_order:
        if battle.field_mgr.terrain(idx) == Terrain.GRASS and \
                not poke_mgr.hidden and \
                battle.pokemons[idx].hp and \
                battle.poke_mgrs[idx].add_hp(ratio=1/16):
            battle.logger.insert(-1, TurnLog(battle.turn, idx, 'グラスフィールド'))

    # うるおいボディ
    for idx in self.speed_order:
        poke = battle.pokemons[idx]
        if poke.ailment.value and poke.hp and poke.ability.name in ['うるおいボディ', 'だっぴ']:
            battle.poke_mgrs[idx].activate_ability()

    # たべのこし
    for idx in self.speed_order:
        poke = battle.pokemons[idx]
        if poke.hp and poke.item.name in ['たべのこし', 'くろいヘドロ']:
            battle.poke_mgrs[idx].activate_item()
            if battle.winner() is not None:
                return

    # アクアリング・ねをはる
    for idx in self.speed_order:
        poke = battle.pokemons[idx]
        poke_mgr = battle.poke_mgrs[idx]

        if poke.hp == 0:
            continue

        h = poke_mgr.hp_drain_amount(int(poke.stats[0]/16), from_opponent=False)
        for cond in [Condition.AQUA_RING, Condition.NEOHARU]:
            if poke_mgr.count[cond] and poke_mgr.add_hp(h):
                battle.logger.insert(-1, TurnLog(battle.turn, idx, cond.name))

    # やどりぎのタネ
    for idx in self.speed_order:
        opp = int(not idx)
        poke = battle.pokemons[idx]
        opponent = battle.pokemons[opp]
        poke_mgr = battle.poke_mgrs[idx]
        opponent_mgr = battle.poke_mgrs[opp]

        if poke_mgr.count[Condition.YADORIGI] and (poke.hp * opponent.hp):
            h = min(poke.hp, int(poke.stats[0]/16))
            # ダメージ処理
            if poke_mgr.add_hp(-h):
                battle.logger.insert(-1, TurnLog(battle.turn, idx, str(Condition.YADORIGI)))
                if battle.winner() is not None:
                    return

                # 回復処理
                if opponent_mgr.add_hp(opponent_mgr.hp_drain_amount(h)):
                    battle.logger.insert(-1, TurnLog(battle.turn, opp, str(Condition.YADORIGI)))
                    if battle.winner() is not None:
                        return

    # 状態異常ダメージ
    for idx in self.speed_order:
        poke = battle.pokemons[idx]
        poke_mgr = battle.poke_mgrs[idx]

        if poke.hp == 0:
            continue

        match poke.ailment:
            case Ailment.PSN:
                if poke.ability.name == 'ポイズンヒール' and poke_mgr.activate_ability():
                    pass
                elif poke_mgr.count[Condition.BAD_POISON]:
                    if poke_mgr.add_hp(ratio=-poke_mgr.count[Condition.BAD_POISON]/16):
                        battle.logger.insert(-1, TurnLog(battle.turn, idx, 'もうどく'))
                        if battle.winner() is not None:
                            return
                elif poke_mgr.add_hp(ratio=-1/8):
                    battle.logger.insert(-1, TurnLog(battle.turn, idx, 'どく'))
                    if battle.winner() is not None:
                        return

                # もうどくカウント
                if poke_mgr.count[Condition.BAD_POISON]:
                    poke_mgr.set_condition(Condition.BAD_POISON, poke_mgr.count[Condition.BAD_POISON]+1)

            case Ailment.BRN:
                if poke_mgr.add_hp(ratio=(-1/32 if poke.ability.name == 'たいねつ' else -1/16)):
                    battle.logger.insert(-1, TurnLog(battle.turn, idx, 'やけど'))
                    if battle.winner() is not None:
                        return

    # 呪いダメージ
    for idx in self.speed_order:
        poke = battle.pokemons[idx]
        poke_mgr = battle.poke_mgrs[idx]

        if poke.hp and poke_mgr.count[Condition.NOROI] and poke_mgr.add_hp(ratio=-0.25):
            battle.logger.insert(-1, TurnLog(battle.turn, idx, '呪い'))
            if battle.winner() is not None:
                return

    # バインドダメージ
    for idx in self.speed_order:
        poke = battle.pokemons[idx]
        poke_mgr = battle.poke_mgrs[idx]

        if poke.hp and poke_mgr.count[Condition.BIND]:
            if poke_mgr.add_hp(ratio=-1/poke_mgr.bind_damage_denom):
                battle.logger.insert(-1, TurnLog(battle.turn, idx, 'バインド'))
                if battle.winner() is not None:
                    return

            poke_mgr.count[Condition.BIND] -= 1
            battle.logger.add(TurnLog(battle.turn, idx, f"バインド 残り{int(poke_mgr.count[Condition.BIND])}ターン"))

    # しおづけダメージ
    for idx in self.speed_order:
        poke = battle.pokemons[idx]

        if poke.hp and poke_mgr.count[Condition.SHIOZUKE]:
            r = 2 if any(t in poke_mgr.types for t in ['みず', 'はがね']) else 1
            if poke_mgr.add_hp(ratio=-r/8):
                battle.logger.insert(-1, TurnLog(battle.turn, idx, 'しおづけ'))

                if battle.winner() is not None:
                    return

    # あめまみれ
    for idx in self.speed_order:
        poke = battle.pokemons[idx]
        poke_mgr = battle.poke_mgrs[idx]

        if poke.hp and poke_mgr.count[Condition.AME_MAMIRE]:
            poke_mgr.add_rank(5, -1)
            poke_mgr.add_condition_count(Condition.AME_MAMIRE, -1)

    # 状態変化のカウント
    for idx in self.speed_order:
        poke = battle.pokemons[idx]
        poke_mgr = battle.poke_mgrs[idx]

        if poke.hp == 0:
            continue

        for cond in [Condition.ENCORE, Condition.HEAL_BLOCK, Condition.KANASHIBARI,
                     Condition.JIGOKUZUKI, Condition.MAGNET_RISE]:
            poke_mgr.add_condition_count(cond, -1)

        # PPが切れたらアンコール解除
        if poke_mgr.expended_moves and poke_mgr.expended_moves[-1].pp == 0:
            poke_mgr.set_condition(Condition.ENCORE, 0)

    # ねむけ判定
    for idx in self.speed_order:
        poke = battle.pokemons[idx]
        poke_mgr = battle.poke_mgrs[idx]

        if poke_mgr.add_condition_count(Condition.NEMUKE, -1):
            if poke_mgr.count[Condition.NEMUKE] == 0:
                # 眠らせる
                poke_mgr.set_ailment(Ailment.SLP, ignore_shinpi=True)

    # ほろびのうた判定
    for idx in self.speed_order:
        poke = battle.pokemons[idx]
        poke_mgr = battle.poke_mgrs[idx]
        if poke.hp and poke_mgr.add_condition_count(Condition.HOROBI, -1):
            if poke_mgr.count[Condition.HOROBI] == 0:
                poke.hp = 0
                battle.logger.add(TurnLog(battle.turn, idx, 'ほろびのうた 瀕死'))
                if battle.winner() is not None:
                    return

    # 場のカウント消費
    for idx in self.speed_order:
        for cond in [SideField.REFLECTOR, SideField.LIGHT_WALL, SideField.SHINPI,
                     SideField.WHITE_MIST, SideField.OIKAZE]:
            battle.field_mgr.add_count(cond, idx, -1)

    for cond in [GlobalField.TRICKROOM, GlobalField.GRAVITY, GlobalField.TERRAIN]:
        battle.field_mgr.add_count(cond, v=-1)

    # 即時アイテムの判定 (ターン終了時)
    for idx in self.speed_order:
        if battle.pokemons[idx].item.immediate and battle.pokemons[idx].hp:
            battle.poke_mgrs[idx].activate_item()

    # はねやすめ解除
    for idx in self.speed_order:
        poke = battle.pokemons[idx]
        if poke_mgr.executed_move.name == 'はねやすめ' and \
                self.move_succeeded[idx] and \
                'ひこう' in poke_mgr.lost_types:
            poke_mgr.lost_types.remove('ひこう')
            battle.logger.add(TurnLog(battle.turn, idx, 'はねやすめ解除'))

    # その他
    for idx in self.speed_order:
        poke = battle.pokemons[idx]
        poke_mgr = battle.poke_mgrs[idx]

        if poke.hp == 0:
            continue

        if poke.ability.name in ['スロースタート', 'かそく', 'しゅうかく', 'ムラっけ', 'ナイトメア']:
            poke_mgr.activate_ability()

        if poke.ability.name == 'はんすう' and poke.ability.count:
            poke_mgr.activate_ability()

        if poke.item.name in ['かえんだま', 'どくどくだま']:
            poke_mgr.activate_item()

        if battle.winner() is not None:
            return
