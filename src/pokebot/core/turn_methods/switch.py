from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Ailment, Condition, SideField, Command
from pokebot.model.ability import Ability
from pokebot.model import Move
from pokebot.logger import TurnLog


def _switch_pokemon(self: TurnManager,
                    idx: PlayerIndex | int,
                    command: Command,
                    baton: dict,
                    landing: bool):

    if not command.is_switch:
        raise Exception(f"Invalid command : {command}")

    poke = self.battle.pokemons[idx]

    # 場のポケモンの特性
    active_ability = poke.ability if poke else Ability()

    # フォルムチェンジ
    if poke and poke.name == 'イルカマン(ナイーブ)':
        poke.change_form('イルカマン(マイティ)')
        self.battle.logger.append(TurnLog(self.battle.turn, idx, '-> マイティフォルム'))

    self.battle.poke_mgrs[idx].bench_reset()

    # 交代
    self.battle.players[idx].team[command.index].active = True

    self._already_switched[idx] = True
    self.battle.pokemons[idx].observed = True  # 観測
    self.battle.logger.append(TurnLog(self.battle.turn, idx, self.battle.command_to_str(idx, command)))

    # Breakpoint破棄
    self.breakpoint[idx] = None

    # 相手の状態をリセット
    opp = int(not idx)
    opponent = self.battle.pokemons[opp]
    opponent_mgr = self.battle.poke_mgrs[opp]

    if opponent:
        # かがくへんかガス解除
        if active_ability.name == 'かがくへんかガス':
            opponent.ability.active = True
            if "immediate" in opponent.ability.tags:
                self.battle.poke_mgrs[opp].activate_ability()
            self.battle.logger.append(TurnLog(self.battle.turn, opp, 'かがくへんかガス解除'))

        # バインド・にげられない状態の解除
        for key in [Condition.BIND, Condition.SWITCH_BLOCK]:
            opponent_mgr.set_condition(key, 0)

    # バトン処理
    if baton:
        poke = self.battle.pokemons[idx]
        poke_mgr = self.battle.poke_mgrs[idx]
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
        self.land([idx])


def _land(self: TurnManager, idxes: list[PlayerIndex | int]):
    """ポケモンが場に出たときの処理"""
    # 設置物の判定
    for idx in idxes:
        poke = self.battle.pokemons[idx]
        poke_mgr = self.battle.poke_mgrs[idx]
        opp = int(not idx)
        opponent = self.battle.pokemons[not idx]

        if poke.item.name != 'あつぞこブーツ':
            if self.battle.field_mgr.count[SideField.STEALTH_ROCK][idx]:
                r_def_type = self.battle.damage_mgr.defence_type_modifier(opp, Move("ステルスロック"))
                ratio = -int(r_def_type/8)
                if poke_mgr.add_hp(ratio=ratio):
                    self.battle.logger.insert(-1, TurnLog(self.battle.turn, idx, f"{SideField.STEALTH_ROCK}"))

            if not poke_mgr.is_floating():
                if self.battle.field_mgr.count[SideField.MAKIBISHI][idx]:
                    d = -int(poke.stats[0] / (10-2*self.battle.field_mgr.count[SideField.MAKIBISHI][idx]))
                    if poke_mgr.add_hp(d):
                        self.battle.logger.insert(-1, TurnLog(self.battle.turn, idx, f"{SideField.MAKIBISHI}"))

                if self.battle.field_mgr.count[SideField.DOKUBISHI][idx]:
                    if 'どく' in poke_mgr.types:
                        self.battle.field_mgr.count[SideField.DOKUBISHI][idx] = 0
                        self.battle.logger.append(TurnLog(self.battle.turn, idx, f"{SideField.DOKUBISHI}解除"))
                    elif poke_mgr.set_ailment(Ailment.PSN, bad_poison=(self.battle.field_mgr.count[SideField.DOKUBISHI][idx] == 2)):
                        self.battle.logger.append(TurnLog(self.battle.turn, idx, f"{SideField.DOKUBISHI}接触"))

                if self.battle.field_mgr.count[SideField.NEBA_NET][idx]:
                    if poke_mgr.add_rank(5, -1, by_opponent=True):
                        self.battle.logger.insert(-1, TurnLog(self.battle.turn, idx, f"{SideField.NEBA_NET}"))

    # 特性の上書き
    for idx in idxes:
        poke = self.battle.pokemons[idx]
        poke_mgr = self.battle.poke_mgrs[idx]
        opp = int(not idx)
        opponent = self.battle.pokemons[not idx]

        # 瀕死ならスキップ
        if poke.hp == 0:
            continue

        if not poke_mgr.is_ability_protected():
            # かがくへんかガス
            if opponent.ability.name == 'かがくへんかガス' and poke.item.name != 'とくせいガード':
                poke.ability.active = False
                self.battle.logger.append(TurnLog(self.battle.turn, idx, 'かがくへんかガス 特性無効'))
                break

            # トレース
            if poke.ability.name == 'トレース' and "unreproducible" not in opponent.ability.tags:
                poke.ability.name = opponent.ability.name
                self.battle.logger.append(TurnLog(self.battle.turn, idx, f"トレース -> {opponent.ability}"))

    # 特性の発動
    for idx in idxes:
        if "immediate_1" in self.battle.pokemons[idx].ability.tags:
            self.battle.poke_mgrs[idx].activate_ability()

    for idx in idxes:
        if "immediate_2" in self.battle.pokemons[idx].ability.tags:
            self.battle.poke_mgrs[idx].activate_ability()

    # 即時アイテムの判定
    for idx in [idxes[0], int(not idxes[0])]:
        poke = self.battle.pokemons[idx]
        if poke.hp and poke.item.immediate:
            self.battle.poke_mgrs[idx].activate_item()
