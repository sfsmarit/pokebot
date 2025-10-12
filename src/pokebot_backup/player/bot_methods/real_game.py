from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import Bot

import os
import time
import shutil
import warnings
from copy import deepcopy

from pokebot.common.enums import Ailment, Time, Phase
from pokebot.model import Pokemon


def _real_game(self: Bot):
    print(f"\n{'#'*50}\n{'対人戦' if self.online else '学校最強大会'}\n{'#'*50}\n")

    if not self.online:
        type(self).press_button('B', n=5)

    # ターン処理
    while True:
        if self.read_phase().value:
            # 操作できるフェーズ
            print(f"{'-'*30} {self.battle.phase.name} phase {'-'*30}")
            if self.online:
                self.nonephase_start_time = 0
            else:
                type(self).press_button('B', n=5, post_sleep=1)  # A連打で遷移した画面から戻る

        else:
            # 操作できないフェーズ
            if not self.online:
                type(self).press_button('A', post_sleep=0.3)
            else:
                # 切断対策
                if not self.nonephase_start_time:
                    self.nonephase_start_time = time.time()
                elif time.time() - self.nonephase_start_time > Time.TIMEOUT.value:
                    print("一定時間応答がないため画面を移動します")
                    type(self).press_button('A', n=10)

            # ターン開始
            self.battle.turn_start_time = time.time()

        match self.battle.phase:
            case Phase.STAND_BY:
                type(self).press_button('A', post_sleep=0.5)

            case Phase.SELECTION:
                if self.battle.selection_indexes[0]:
                    continue

                t0 = time.time()  # 計測開始

                # 試合をリセット
                self.battle.init_game()

                # OCR履歴を削除
                if os.path.isdir(type(self).ocr_log_dir):
                    shutil.rmtree(type(self).ocr_log_dir)
                    print("OCR履歴を削除しました")

                # 相手のパーティを読み込む
                type(self).press_button('B', n=5)
                self.read_opponent_team()
                dt = time.time() - t0

                # コマンドを取得
                commands = self.battle.player[0].selection_commands(deepcopy(self.battle))
                self.battle.selection_indexes[0] = [cmd.index for cmd in commands]

                labels = [self.battle.player[0].team[i].label for i in self.battle.selection_indexes[0]]
                print(f"{'='*50}\n選出 {labels}\n{'='*50}")

                # コマンド入力
                t0 = time.time()
                self.input_selection_command(commands)
                dt += time.time() - t0
                print(f"操作時間 {dt:.1f}s")

                # 入力時間を更新
                self.battle.selection_input_time = max(self.battle.selection_input_time, dt)

                self.battle.turn = 0  # 0ターン目終了

            case Phase.ACTION:
                t0 = time.time()  # 計測開始

                if not self.online:
                    type(self).press_button('B')  # A連打による画面遷移対策

                # 盤面の状態を取得
                if not self.read_banmen():
                    warnings.warn('Failed to read Banmen')
                    type(self).press_button('B', n=5)
                else:
                    self.process_text_buffer()  # バッファを処理

                    # TODO 現在の (すなわち前ターン終了時の) 状態を記録
                    pass

                    # 前ターンの処理を反映
                    for idx in range(2):
                        poke = self.battle.pokemons[idx]
                        poke_mgr = self.battle.poke_mgrs[idx]

                        if poke_mgr.expended_moves:
                            poke_mgr.active_turn += 1

                            # こだわりロック
                            if poke.item.name[:4] == 'こだわり' and not poke_mgr.choice_locked:
                                poke_mgr.choice_locked = True

                        # 眠りターン消費
                        if poke.ailment == Ailment.SLP and poke.sleep_count:
                            poke.sleep_count -= 1

                    # 相手の場のポケモンを表示
                    print(f"\n相手\t{self.battle.pokemons[1]}")

                    # コマンドを取得
                    dt = time.time() - t0
                    command = self.battle.player[0].action_command(deepcopy(self.battle))
                    print(f"{'='*50}\n\t{self.battle.command_to_str(0, command)}\n{'='*50}")
                    t0 = time.time()

                    self.battle.turn += 1  # ターン経過

                    # コマンド入力
                    if self.input_action_command(command):
                        dt += time.time() - t0
                        print(f"操作時間 {dt:.1f}s")

                        # 入力時間を更新
                        self.battle.action_input_time = max(self.battle.action_input_time, dt)

                        # コマンドによる盤面の変化を
                        if command.is_switch:
                            self.battle.turn_mgr.switch_pokemon(0, command=command, landing=False)
                        else:
                            if command.is_terastal:
                                self.battle.pokemons[0].terastallize()

                            # 画面テキストを読み取れなかった場合を想定して、暫定的に選択した技が実行されたとして記録しておく
                            move = self.battle.pokemons[0].moves[command.index]
                            self.battle.poke_mgrs[0].expended_moves.append(move)
                            self.battle.poke_mgrs[0].executed_move = move

                        time.sleep(1)  # 連続入力対策

                    else:
                        warnings.warn(f"Failed to input commands")
                        type(self).press_button('B', n=5)
                        continue

                    self.recognized_labels.clear()  # 読み取り履歴を削除

            case Phase.SWITCH:
                t0 = time.time()  # 計測開始

                if not self.online:
                    type(self).press_button('B', n=4, post_sleep=0.5)  # A連打による画面遷移対策
                    if self.read_phase() != Phase.SWITCH:
                        continue

                for i in range(len(self.battle.selection_indexes[0])):
                    poke = Pokemon.find(self.battle.selected_pokemons(0), label=self._read_switch_label(i))
                    if not poke:
                        continue

                    poke.active = i == 0

                    # HPを更新
                    hp = self._read_switch_hp(i, capture=(i == 0))
                    if hp == 0:
                        hp = self._read_switch_hp(i, capture=True)  # 0なら再読み取り
                    poke.hp = hp
                    print(f"\t{poke.name} HP {poke.hp}/{poke.stats[0]}")

                self.process_text_buffer()  # テキストバッファ処理

                # コマンドを取得
                dt = time.time() - t0
                command = self.battle.player[0].switch_command(deepcopy(self.battle))
                print(f"{'='*50}\n\t{self.battle.command_to_str(0, command)}\n{'='*50}")
                t0 = time.time()

                # コマンド入力
                self.input_switch_command(command)

                # 入力時間を更新
                dt += time.time() - t0
                print(f"操作時間 {dt:.1f}s")
                self.battle.switch_input_time = max(self.battle.switch_input_time, dt)

                # 交代
                self.battle.turn_mgr.switch_pokemon(0, command=command, landing=False)

                self.recognized_labels.clear()  # 読み取り履歴を削除
                time.sleep(2)  # 連続入力対策

            case _:
                # 試合開始前ならスキップ
                if not self.battle.selection_indexes[1]:
                    continue

                # 画面のテキストを取得
                if self.read_screen_text(capture=False):
                    # オフライン対戦で次の試合に移行していたら中断
                    if self.battle.winner() is not None:
                        return
                    # 特性テキストを取得
                    for pidx in range(2):
                        self.read_ability_text(pidx, capture=False)

                if not self.online:
                    type(self).press_button('A', post_sleep=0.5)

                elif (text := self._read_win_loss(capture=False)):
                    # 勝敗の観測
                    self.battle._winner = 0 if text == 'win' else 1
                    return

                self.recognized_labels.clear()  # 読み取り履歴を削除
