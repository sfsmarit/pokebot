from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Ailment, Condition, SideField, Command
from pokebot.core.ability import Ability
from pokebot.core import Move
from pokebot.logger import TurnLog


def _switch_pokemon(self: TurnManager,
                    idx: PlayerIndex,
                    command: Command,
                    baton: dict,
                    landing: bool):

    if not command.is_switch:
        raise Exception(f"Invalid command : {command}")

    # 場のポケモンの特性
    active_ability = Ability()

    # 場のポケモンを控えに戻す
    if (poke := self.battle.pokemon[idx]):
        active_ability = poke.ability
        poke.bench_reset()

        # フォルムチェンジ
        if poke.name == 'イルカマン(ナイーブ)':
            poke.change_form('イルカマン(マイティ)')
            self.battle.logger.append(TurnLog(self.battle.turn, idx, '-> マイティフォルム'))

        self.switch_command_history[idx].append(command)

    # 交代
    self.battle.player[idx].team[command.index].active = True

    self._already_switched[idx] = True
    self.battle.pokemon[idx].observed = True
    self.battle.logger.append(TurnLog(self.battle.turn, idx, self.battle.command_to_str(idx, command)))

    # Breakpoint破棄
    self.breakpoint[idx] = None

    # 相手の状態をリセット
    opp = PlayerIndex(not idx)
    opponent = self.battle.pokemon[opp]
    opponent_mgr = self.battle.poke_mgr[opp]

    if opponent:
        # かがくへんかガス解除
        if active_ability.name == 'かがくへんかガス':
            opponent.ability.active = True
            if "immediate" in opponent.ability.tags:
                self.battle.poke_mgr[opp].activate_ability()
            self.battle.logger.append(TurnLog(self.battle.turn, opp, 'かがくへんかガス解除'))

        # バインド・にげられない状態の解除
        for key in [Condition.BIND, Condition.SWITCH_BLOCK]:
            opponent_mgr.set_condition(key, 0)

    # バトン処理
    if baton:
        poke = self.battle.pokemon[idx]
        poke_mgr = self.battle.poke_mgr[idx]
        for key in baton:
            if isinstance(key, Condition):
                poke_mgr.count[key] = baton[key]
                self.battle.logger.append(TurnLog(self.battle.turn, idx, f"継承 {key} {baton[key]}"))
            elif key == 'sub_hp':
                poke_mgr.sub_hp = baton[key]
                self.battle.logger.append(TurnLog(self.battle.turn, idx, f"継承 みがわり HP{baton[key]}"))
            elif key == 'rank':
                poke_mgr.rank = baton[key]
                self.battle.logger.append(TurnLog(self.battle.turn, idx, f"継承 ランク {baton[key][1:]}"))

    # 行動順の更新
    self.update_speed_order()

    # 着地処理
    if landing:
        self.land(idx)


def _land(self: TurnManager, idx: PlayerIndex):
    """ポケモンが場に出たときの処理"""
    battle = self.battle

    opp = PlayerIndex(not idx)
    poke = battle.pokemon[idx]
    poke_mgr = battle.poke_mgr[idx]

    # 設置物の判定
    if poke.item != 'あつぞこブーツ':
        if battle.field_mgr.count[SideField.STEALTH_ROCK][idx]:
            r_def_type = battle.damage_mgr.defence_type_modifier(opp, Move("ステルスロック"))
            ratio = -int(r_def_type/8)
            if poke_mgr.add_hp(ratio=ratio):
                battle.logger.insert(-1, TurnLog(battle.turn, idx, f"{SideField.STEALTH_ROCK}"))

        if not poke_mgr.is_floating():
            if battle.field_mgr.count[SideField.MAKIBISHI][idx]:
                d = -int(poke.stats[0] / (10-2*battle.field_mgr.count[SideField.MAKIBISHI][idx]))
                if poke_mgr.add_hp(d):
                    battle.logger.insert(-1, TurnLog(battle.turn, idx, f"{SideField.MAKIBISHI}"))

            if battle.field_mgr.count[SideField.DOKUBISHI][idx]:
                if 'どく' in poke_mgr.types:
                    battle.field_mgr.count[SideField.DOKUBISHI][idx] = 0
                    battle.logger.append(TurnLog(battle.turn, idx, f"{SideField.DOKUBISHI}解除"))
                elif poke_mgr.set_ailment(Ailment.PSN, bad_poison=(battle.field_mgr.count[SideField.DOKUBISHI][idx] == 2)):
                    battle.logger.append(TurnLog(battle.turn, idx, f"{SideField.DOKUBISHI}接触"))

            if battle.field_mgr.count[SideField.NEBA_NET][idx]:
                if poke_mgr.add_rank(5, -1, by_opponent=True):
                    battle.logger.insert(-1, TurnLog(battle.turn, idx, f"{SideField.NEBA_NET}"))

    # 瀕死なら中断
    if poke.hp == 0:
        return

    # 特性の発動
    for i in [idx, opp]:
        p1 = battle.pokemon[i]
        p2 = battle.pokemon[not i]

        if not battle.poke_mgr[i].is_ability_protected():
            if p2.ability.name == 'かがくへんかガス' and p1.item != 'とくせいガード':
                # かがくへんかガス
                p1.ability.active = False
                battle.logger.append(TurnLog(battle.turn, i, 'かがくへんかガス 特性無効'))
                break

            elif p1.ability.name == 'トレース' and "unreproducible" in p2.ability.tags:
                # トレース
                p1.ability.name = p2.ability.name
                battle.logger.append(TurnLog(battle.turn, i, f"トレース -> {p2.ability}"))

        if "immediate" in p1.ability.tags:
            battle.poke_mgr[i].activate_ability()

    # 即時アイテムの判定
    for i in [idx, opp]:
        p1 = battle.pokemon[i]
        if p1.item.immediate and p1.hp:
            battle.poke_mgr[i].activate_item()
