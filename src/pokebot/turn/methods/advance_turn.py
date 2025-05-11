from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Ailment, Condition, MoveCategory, \
    Command, Phase
from pokebot.core import PokeDB, Move
from pokebot.logger import TurnLog, CommandLog
from pokebot.move import hit_probability, num_strikes


def _advance_turn(self: TurnManager,
                  commands: list[Command],
                  switch_commands: list[Command]):
    """
    _summary_

    盤面を1ターン進める
    ----------
    self : TurnManager
        _description_
    commands : list[int  |  None], optional
        ターン開始時に両プレイヤーが入力するコマンド, by default [None]*2
    switch_commands : list[int  |  None], optional
        交代時に両プレイヤーが入力するコマンド, by default [None]*2
    """

    battle = self.battle

    # ターンの初期化
    if not any(self.breakpoint):
        self.init_turn()
        battle.turn += 1

    if battle.turn == 0:
        # 0ターン目は先頭のポケモンを場に出して終了
        if not any(self.breakpoint):
            # 交代
            for i in range(2):
                self.switch_pokemon(PlayerIndex(i),
                                    switch_idx=battle.selection_indexes[i][0],
                                    landing=False)

            # 着地処理 (両者が場に出た後に行う)
            for i in self.speed_order:
                self.land(i)

            # だっしゅつパック判定 (0ターン目)
            if (idxes := [i for i in self.speed_order if self.is_ejectpack_triggered(i)]):
                self.breakpoint[idxes[0]] = "ejectpack_turn0"
                battle.pokemon[idxes[0]].item.consume()
                for idx in idxes:
                    battle.poke_mgr[idx].rank_dropped = False

        # だっしゅつパックによる交代
        if (s := "ejectpack_turn0") in self.breakpoint:
            idx = PlayerIndex(self.breakpoint.index(s))
            self.switch_pokemon(idx, command=switch_commands[idx])
            # コマンド破棄
            switch_commands[idx] = Command.NONE

        # このターンに入力されたコマンドを記録
        battle.logger.append(CommandLog(battle.turn, self.command, self.switch_command_history))

        return

    if not any(self.breakpoint):
        # コマンドを取得
        for idx in range(2):
            if commands[idx] == Command.NONE:
                # 方策関数に従う
                battle.phase = Phase.BATTLE
                self.command[idx] = battle.player[idx].battle_command(battle.masked(PlayerIndex(idx), called=True))
                battle.phase = Phase.NONE
            else:
                # 引数のコマンドを使う
                self.command[idx] = commands[idx]

            text = battle.pokemon[idx].name
            if battle.pokemon[idx].terastal:
                text += f"_{battle.pokemon[idx].terastal}T"

            battle.logger.append(TurnLog(battle.turn, idx, text))
            battle.logger.append(TurnLog(battle.turn, idx, f"HP {battle.pokemon[idx].hp}/{battle.pokemon[idx].stats[0]}"))
            battle.logger.append(TurnLog(battle.turn, idx, f"コマンド {self.command[idx].name}"))

        # 行動順を更新
        self.update_action_order()

        for idx in range(2):
            text = '先手' if battle.poke_mgr[idx].first_act else '後手'
            battle.logger.append(TurnLog(battle.turn, idx, text))
            # TODO 高速化 相手の素早さを推定
            # self.estimate_opponent_speed(PlayerIndex(idx))

    for idx in range(2):
        idx = PlayerIndex(idx)

        # 交代
        if not any(self.breakpoint) and self.command[idx].is_switch:
            self.switch_pokemon(idx, command=self.command[idx])

            # だっしゅつパック判定 (交代後)
            if (idxes := [i for i in self.speed_order if self.is_ejectpack_triggered(i)]):
                self.breakpoint[idxes[0]] = f"ejectpack_switch_{idx}"
                battle.pokemon[idxes[0]].item.consume()
                for i in idxes:
                    battle.poke_mgr[i].rank_dropped = False

        # だっしゅつパックによる交代
        if (s := f"ejectpack_switch_{idx}") in self.breakpoint:
            i = PlayerIndex(self.breakpoint.index(s))
            self.switch_pokemon(i, command=switch_commands[i])
            # コマンド破棄
            switch_commands[idx] = Command.NONE

    if not any(self.breakpoint):
        for idx in range(2):
            if self.command[idx].is_terastal:
                # テラスタル発動
                battle.pokemon[idx].terastallize()
                battle.logger.append(TurnLog(battle.turn, idx, f"テラスタル {battle.pokemon[idx].terastal}"))

                # 特性発動
                if battle.pokemon[idx].ability.name in ['おもかげやどし', 'ゼロフォーミング']:
                    battle.poke_mgr[idx].activate_ability()

    # 行動処理
    for idx in battle.action_order:
        dfn = PlayerIndex(not idx)
        attacker_mgr = battle.poke_mgr[idx]
        defender_mgr = battle.poke_mgr[dfn]
        move = self.move[idx]

        if not any(self.breakpoint):
            self.init_act()

            # 行動スキップ (特殊コマンド)
            if self.command[idx] == Command.SKIP:
                battle.logger.append(TurnLog(battle.turn, idx, '行動スキップ'))
                battle.poke_mgr[idx].no_act()
                continue

            # このターンに交代していたら行動できない
            if self._already_switched[idx]:
                continue

            # みちづれ/おんねん解除
            battle.poke_mgr[idx].count[Condition.MICHIZURE] = 0

            # 反動
            if not move:
                battle.logger.append(TurnLog(battle.turn, idx, '行動不能 反動'))
                battle.poke_mgr[idx].no_act()
                continue

            # ねむりカウント消費
            if battle.pokemon[idx].ailment == Ailment.SLP:
                battle.poke_mgr[idx].reduce_sleep_count(
                    by=(2 if battle.pokemon[idx].ability.name == 'はやおき' else 1))

            # ねむり行動不能
            if battle.pokemon[idx].ailment == Ailment.SLP and "sleep" not in move.tags:
                battle.poke_mgr[idx].no_act()
                continue

            # こおり判定
            elif battle.pokemon[idx].ailment == Ailment.FLZ:
                if "unfreeze" in move.tags or battle.random.random() < 0.2:
                    # こおり解除
                    attacker_mgr.set_ailment(Ailment.NONE)
                else:
                    battle.poke_mgr[idx].no_act()
                    battle.logger.append(TurnLog(battle.turn, idx, '行動不能 こおり'))
                    continue

            # なまけ判定
            if battle.pokemon[idx].ability.name == 'なまけ':
                battle.pokemon[idx].ability.count += 1
                if battle.pokemon[idx].ability.count % 2 == 0:
                    battle.poke_mgr[idx].no_act()
                    battle.logger.append(TurnLog(battle.turn, idx, '行動不能 なまけ'))
                    continue

            # ひるみ判定
            if self._flinch:
                battle.poke_mgr[idx].no_act()
                battle.logger.append(TurnLog(battle.turn, idx, '行動不能 ひるみ'))
                if battle.pokemon[idx].ability.name == 'ふくつのこころ':
                    attacker_mgr.activate_ability()
                continue

            # 挑発などにより、本来選択できない技が選ばれていれば中断する
            if battle.poke_mgr[idx].unresponsive_turn == 0:
                is_choosable, reason = attacker_mgr.can_choose_move(move)
                if not is_choosable:
                    battle.poke_mgr[idx].no_act()
                    battle.logger.append(TurnLog(battle.turn, idx, f"{move} 不発 ({reason})"))
                    continue

            # こんらん判定
            if attacker_mgr.add_condition_count(Condition.CONFUSION, -1):
                # 自傷判定
                if battle.random.random() < 0.25:
                    mv = Move('わるあがき')
                    damages = battle.damage_mgr.single_hit_damages(idx, mv, self_damage=True)
                    battle.logger.insert(-1, TurnLog(battle.turn, idx, 'こんらん自傷'))
                    attacker_mgr.add_hp(-battle.random.choice(damages), move=mv)
                    battle.poke_mgr[idx].no_act()
                    continue

            # しびれ判定
            if battle.pokemon[idx].ailment == Ailment.PAR and battle.random.random() < 0.25:
                battle.poke_mgr[idx].no_act()
                battle.logger.append(TurnLog(battle.turn, idx, '行動不能 しびれ'))
                continue

            # メロメロ判定
            if battle.poke_mgr[idx].count[Condition.MEROMERO] and battle.random.random() < 0.5:
                battle.poke_mgr[idx].no_act()
                battle.logger.append(TurnLog(battle.turn, idx, '行動不能 メロメロ'))
                continue

            # --- ここで行動できることが確定 ---
            # PP消費
            if move.name != 'わるあがき':
                # PPを消費する技の確定
                battle.poke_mgr[idx].expended_moves.append(move)

                # 命令できる状態ならPPを消費する
                if battle.poke_mgr[idx].unresponsive_turn == 0:
                    move.add_pp(-2 if battle.pokemon[dfn].ability.name == 'プレッシャー' else -1)
                    move.observed = True
                    battle.logger.append(TurnLog(battle.turn, idx, f"{move} PP {move.pp}"))

            # ねごとによる技の変更
            if move.name == 'ねごと':
                if self.can_execute_move(idx, move):
                    move = battle.random.choice(battle.pokemon[idx].get_negoto_moves())
                    move.observed = True
                    battle.logger.append(TurnLog(battle.turn, idx, f"ねごと -> {move}"))
                else:
                    self.move_succeeded[idx] = False

            # まもる技の連発と、場に出たターンしか使えない技の失敗
            for tag in ['protect', 'first_turn']:
                self.move_succeeded[idx] &= self.can_execute_move(idx, move, tag=tag)

            # 発動する技の確定
            battle.poke_mgr[idx].executed_move = move if self.move_succeeded[idx] else Move()

            # こだわり固定
            if (battle.pokemon[idx].item.name[:4] == 'こだわり' or battle.pokemon[idx].ability.name == 'ごりむちゅう'):
                battle.poke_mgr[idx].choice_locked = True

            # 技の発動失敗
            # 本来、じばく技の判定はリベロ判定の後だが、実装の簡略化のためにまとめて行う
            self.move_succeeded[idx] &= self.can_execute_move(idx, move)

            # リベロ判定
            if battle.pokemon[idx].ability.name in ['へんげんじざい', 'リベロ'] and self.move_succeeded[idx]:
                attacker_mgr.activate_ability(move)

            # 溜め技
            if any(tag in move.tags for tag in ["charge", "hide"]):
                # 溜め判定
                battle.poke_mgr[idx].unresponsive_turn = int(battle.poke_mgr[idx].unresponsive_turn == 0)
                # 行動不能
                if battle.poke_mgr[idx].unresponsive_turn and not self.charge_move(idx, move):
                    continue

            # 隠れ状態の解除
            battle.poke_mgr[idx].hidden = False

            # HPコストの消費
            if PokeDB.get_move_effect_value(move, "cost") and \
                    self.move_succeeded[idx] and \
                    attacker_mgr.apply_move_recoil(move, 'cost'):
                if battle.winner() is not None:
                    return

            # 技が無効なら中断
            if not self.move_succeeded[idx]:
                battle.logger.append(TurnLog(battle.turn, idx, f"{move} 失敗"))
                continue

            # 相手のまもる技により攻撃を防がれたら中断
            if self.process_protection(idx, move):
                continue

            # 技の発動回数の確定
            self._n_strikes = num_strikes(battle, idx, move)
            if self._n_strikes > 1:
                battle.logger.append(TurnLog(battle.turn, idx, f"{self._n_strikes}発"))

            # 命中判定
            is_hit = battle.random.random() < hit_probability(battle, idx, move)

            for cnt in range(self._n_strikes):
                # 技を外したら中断
                if not is_hit:
                    if cnt == 0:
                        # 1発目の外し
                        self.process_on_miss(idx, move)
                    else:
                        # 連続技の中断
                        battle.logger.append(TurnLog(battle.turn, idx, f"{cnt}ヒット"))
                    break

                # 技の発動処理
                if move.category == MoveCategory.STA:
                    self.process_status_move(idx, move)
                else:
                    self.process_attack_move(idx, move, combo_count=cnt)

                # 反射で攻守反転
                if self._move_was_mirrored:
                    idx, dfn = dfn, idx

                # 技を無効化する特性の処理
                if self._move_was_negated_by_ability:
                    self.process_negating_ability(dfn)

                # 即時アイテムの判定 (攻撃直後)
                for i in [idx, dfn]:
                    if battle.pokemon[i].item.immediate and battle.pokemon[i].hp:
                        battle.poke_mgr[i].activate_item()

                # どちらか一方が瀕死なら攻撃を中断
                if battle.pokemon[idx].hp * battle.pokemon[dfn].hp == 0:
                    break

                # 特定の技では、一発ごとに命中判定を行う
                if move.name in ["トリプルアクセル", "ネズミざん"]:
                    is_hit = battle.random.random() < hit_probability(battle, idx, move)

            # 技の発動後の処理
            battle.poke_mgr[idx].active_turn += 1
            battle.logger.append(TurnLog(battle.turn, idx, f"{move} {'成功' if self.move_succeeded[idx] else '失敗'}"))

            # ステラ強化タイプの消費
            self.consume_stellar(idx, move)

            # 反動で動けない技の反動を設定
            if self.move_succeeded[idx]:
                attacker_mgr.process_tagged_move(move, 'immovable')

            if self.damage_dealt[idx]:
                # 攻撃側の特性発動
                if battle.pokemon[idx].ability.name in ['じしんかじょう', 'しろのいななき', 'じんばいったい',
                                                        'くろのいななき', 'マジシャン']:
                    attacker_mgr.activate_ability()

                # 防御側の特性発動
                if battle.pokemon[dfn].ability.name in ['へんしょく', 'ぎゃくじょう', 'いかりのこうら']:
                    defender_mgr.activate_ability(move)

                battle.poke_mgr[dfn].berserk_triggered = False

                # 被弾時のアイテム発動
                if battle.pokemon[dfn].hp and \
                        battle.pokemon[dfn].item.name in ['レッドカード', 'アッキのみ', 'タラプのみ']:
                    defender_mgr.activate_item(move)

                # 攻撃後のアイテム発動
                if battle.pokemon[idx].item.name in ['いのちのたま', 'かいがらのすず']:
                    attacker_mgr.activate_item()

            # TODO ききかいひ・にげごし判定
            # TODO わるいてぐせ判定

            # だっしゅつボタン判定
            if battle.pokemon[dfn].item.name == 'だっしゅつボタン' and \
                    defender_mgr.activate_item():
                self.breakpoint[not idx] = "ejectbutton"

        # だっしゅつボタンによる交代
        ejectbutton_triggered = False
        if self.breakpoint[dfn] == "ejectbutton":
            self.switch_pokemon(dfn, command=switch_commands[dfn])
            # コマンド破棄
            switch_commands[dfn] = Command.NONE
            ejectbutton_triggered = True

        if not any(self.breakpoint):
            # 技の追加処理
            if move.name in ['アイアンローラー', 'アイススピナー', 'でんこうそうげき', 'もえつきる']:
                attacker_mgr.activate_move_effect(move)

            # 交代技の処理
            if "U-turn" in move.tags:
                if move.name in ['クイックターン', 'とんぼがえり', 'ボルトチェンジ'] and \
                        ejectbutton_triggered:
                    battle.logger.append(TurnLog(battle.turn, idx, f"交代失敗"))

                elif self.move_succeeded[idx]:
                    if move.name == 'すてゼリフ' and \
                            defender_mgr.defending_ability(move) == "マジックミラー":
                        target_idx = dfn
                    else:
                        target_idx = idx

                    if battle.switchable_indexes(target_idx):
                        self.breakpoint[idx] = f"Uturn_{target_idx}"

        # 技による交代
        Uturned = False

        if (s := f"Uturn_{idx}") in self.breakpoint:
            idx = PlayerIndex(self.breakpoint.index(s))
            baton = {}

            match move.name:
                case 'しっぽきり':
                    baton['sub_hp'] = int(battle.pokemon[idx].stats[0]/4)
                case 'バトンタッチ':
                    if any(battle.poke_mgr[idx].rank):
                        baton['rank'] = battle.poke_mgr[idx].rank.copy()
                    if battle.poke_mgr[idx].sub_hp:
                        baton['sub_hp'] = battle.poke_mgr[idx].sub_hp

                    baton_cond = [key for key, val in battle.poke_mgr[idx].count.items() if key.is_baton and val]
                    for cond in baton_cond:
                        baton[cond] = battle.poke_mgr[idx].count[cond]

            self.switch_pokemon(idx, command=switch_commands[idx], baton=baton)
            Uturned = True
            # コマンド破棄
            switch_commands[idx] = Command.NONE

        if not any(self.breakpoint):
            if not ejectbutton_triggered and not Uturned:
                # だっしゅつパック判定 (わざ発動後)
                if (idxes := [i for i in self.speed_order if self.is_ejectpack_triggered(i)]):
                    self.breakpoint[idxes[0]] = f"ejectpack_move_{idx}"
                    battle.pokemon[idxes[0]].item.consume()
                    for i in idxes:
                        battle.poke_mgr[i].rank_dropped = False

        # だっしゅつパックによる交代
        if (s := f"ejectpack_move_{idx}") in self.breakpoint:
            idx = PlayerIndex(self.breakpoint.index(s))
            self.switch_pokemon(idx, command=switch_commands[idx])
            # コマンド破棄
            switch_commands[idx] = Command.NONE

        if not any(self.breakpoint):
            # あばれる状態の判定
            attacker_mgr.process_tagged_move(move, 'rage')

            # のどスプレー判定
            if battle.pokemon[idx].hp and battle.pokemon[idx].item.name == 'のどスプレー':
                attacker_mgr.activate_item(move)

            # 即時アイテムの判定 (手番が移る直前)
            if battle.pokemon[idx].item.immediate and battle.pokemon[idx].hp:
                attacker_mgr.activate_item()

            # 後手が瀕死なら中断
            if battle.pokemon[dfn].hp == 0:
                break

    if not any(self.breakpoint):
        if battle.winner() is not None:
            return

        # ターン終了時の処理
        self.end_turn()

        if battle.winner() is not None:
            return

        # だっしゅつパック判定 (ターン終了時)
        if (idxes := [i for i in self.speed_order if self.is_ejectpack_triggered(i)]):
            self.breakpoint[idxes[0]] = 'ejectpack_end'
            battle.pokemon[idxes[0]].item.consume()
            for i in idxes:
                battle.poke_mgr[i].rank_dropped = False

    # だっしゅつパックによる交代
    if (s := 'ejectpack_end') in self.breakpoint:
        idx = PlayerIndex(self.breakpoint.index(s))
        self.switch_pokemon(idx, command=switch_commands[idx])
        # コマンド破棄
        switch_commands[idx] = Command.NONE

    # 場のポケモンが瀕死なら交代
    while battle.winner() is None:
        idxes = []

        # 交代するプレイヤーを決定
        if not any(self.breakpoint):
            idxes = [i for i in range(2) if battle.pokemon[i].hp == 0]
            for i in idxes:
                self.breakpoint[i] = 'fainting'
        else:
            idxes = [i for i in range(2) if self.breakpoint[i] == 'fainting']

        if not idxes:
            break

        # 交代
        for idx in idxes:
            self.switch_pokemon(PlayerIndex(idx), command=switch_commands[idx], landing=False)
            # コマンド破棄
            switch_commands[idx] = Command.NONE

        # 両者が死に出しした場合は、素早さ順に処理する
        if len(idxes) > 1:
            idxes = self.speed_order

        # 着地処理
        for idx in idxes:
            self.land(PlayerIndex(idx))

    # このターンに入力されたコマンドを記録
    battle.logger.append(CommandLog(battle.turn, self.command, self.switch_command_history))
