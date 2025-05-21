from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Command, Phase
from pokebot.logger import TurnLog, CommandLog


def _advance_turn(self: TurnManager,
                  commands: list[Command],
                  switch_commands: list[Command]):
    # 初期化
    if not any(self.breakpoint):
        self.init_turn()
        self.battle.turn += 1

    # 0ターン目は先頭のポケモンを場に出して終了
    if self.battle.turn == 0:
        if not any(self.breakpoint):
            # 交代 (地処理は両プレイヤーのポケモンが場に出た後に行う)
            for i in range(2):
                self.switch_pokemon(i, switch_idx=self.battle.selection_indexes[i][0], landing=False)

            # 着地処理
            for i in self.speed_order:
                self.land(i)

            # だっしゅつパック判定
            switch_indexes = [i for i in self.speed_order if self.is_ejectpack_triggered(i)]
            if switch_indexes:
                self.breakpoint[switch_indexes[0]] = "ejectpack_turn0"  # 先手のみ交代
                self.battle.pokemons[switch_indexes[0]].item.consume()
                for idx in switch_indexes:
                    self.battle.poke_mgrs[idx].rank_dropped = False  # フラグをリセット

        # だっしゅつパックによる交代
        if (s := "ejectpack_turn0") in self.breakpoint:
            idx = self.breakpoint.index(s)
            self.switch_pokemon(idx, command=switch_commands[idx])
            switch_commands[idx] = Command.NONE  # コマンド破棄

        # コマンドを記録
        self.battle.logger.append(CommandLog(self.battle.turn, self.command, self.switch_history))

        return

    if not any(self.breakpoint):
        # コマンドを取得
        for idx in range(2):
            if commands[idx] == Command.NONE:
                # 方策関数に従う
                self.battle.phase = Phase.ACTION
                masked = self.battle.masked(idx, called=True)
                self.command[idx] = self.battle.players[idx].action_command(masked)
                self.battle.phase = Phase.NONE
            else:
                # 引数のコマンドに従う
                self.command[idx] = commands[idx]

            text = self.battle.pokemons[idx].name
            if self.battle.pokemons[idx].terastal:
                text += f"_{self.battle.pokemons[idx].terastal}T"
            self.battle.logger.append(TurnLog(self.battle.turn, idx, text))
            self.battle.logger.append(TurnLog(self.battle.turn, idx, f"HP {self.battle.pokemons[idx].hp}/{self.battle.pokemons[idx].stats[0]}"))
            self.battle.logger.append(TurnLog(self.battle.turn, idx, f"コマンド {self.command[idx].name}"))

        # 行動順を更新
        self.update_action_order()

        for idx in range(2):
            text = '先手' if self.battle.poke_mgrs[idx].first_act else '後手'
            self.battle.logger.append(TurnLog(self.battle.turn, idx, text))

            # TODO 高速化 相手のS推定
            # self.estimate_opponent_speed(idx)

    for idx in range(2):
        if not any(self.breakpoint):
            # ターンコマンドによる交代
            if self.command[idx].is_switch:
                self.switch_pokemon(idx, command=self.command[idx])

                # だっしゅつパック判定
                if (idxes := [i for i in self.speed_order if self.is_ejectpack_triggered(i)]):
                    self.breakpoint[idxes[0]] = f"ejectpack_switch_{idx}"
                    self.battle.pokemons[idxes[0]].item.consume()
                    for i in idxes:
                        self.battle.poke_mgrs[i].rank_dropped = False

        # だっしゅつパックによる交代
        if (s := f"ejectpack_switch_{idx}") in self.breakpoint:
            i = self.breakpoint.index(s)
            self.switch_pokemon(i, command=switch_commands[i])
            switch_commands[idx] = Command.NONE  # コマンド破棄

    if not any(self.breakpoint):
        # ターン行動前の処理
        for idx in range(2):
            if self.command[idx].is_terastal:
                # テラスタル発動
                self.battle.pokemons[idx].terastallize()
                self.battle.logger.append(TurnLog(self.battle.turn, idx, f"テラスタル {self.battle.pokemons[idx].terastal}"))

                # 特性発動
                if self.battle.pokemons[idx].ability.name in ['おもかげやどし', 'ゼロフォーミング']:
                    self.battle.poke_mgrs[idx].activate_ability()

    # ターン行動
    for idx in self.battle.action_order:
        dfn = int(not idx)
        attacker_mgr = self.battle.poke_mgrs[idx]
        defender_mgr = self.battle.poke_mgrs[dfn]
        move = self.move[idx]

        if not any(self.breakpoint):
            self.process_turn_action(idx)

        # だっしゅつボタンによる交代
        ejectbutton_triggered = False
        if self.breakpoint[dfn] == "ejectbutton":
            self.switch_pokemon(dfn, command=switch_commands[dfn])
            switch_commands[dfn] = Command.NONE  # コマンド破棄
            ejectbutton_triggered = True

        if not any(self.breakpoint):
            # 技の追加処理
            if move.name in ['アイアンローラー', 'アイススピナー', 'でんこうそうげき', 'もえつきる']:
                attacker_mgr.activate_move_effect(move)

            # 技による交代判定
            if "U-turn" in move.tags:
                if move.name in ['クイックターン', 'とんぼがえり', 'ボルトチェンジ'] and ejectbutton_triggered:
                    self.battle.logger.append(TurnLog(self.battle.turn, idx, f"交代失敗"))
                elif self.move_succeeded[idx]:
                    if move.name == 'すてゼリフ' and defender_mgr.defending_ability(move) == "マジックミラー":
                        target_idx = dfn
                    else:
                        target_idx = idx

                    if self.battle.switchable_indexes(target_idx):
                        self.breakpoint[idx] = f"Uturn_{target_idx}"

        # 技による交代
        Uturned = False
        if (s := f"Uturn_{idx}") in self.breakpoint:
            idx = self.breakpoint.index(s)
            baton = {}

            match move.name:
                case 'しっぽきり':
                    baton['sub_hp'] = int(self.battle.pokemons[idx].stats[0]/4)
                case 'バトンタッチ':
                    if any(self.battle.poke_mgrs[idx].rank):
                        baton['rank'] = self.battle.poke_mgrs[idx].rank.copy()
                    if self.battle.poke_mgrs[idx].sub_hp:
                        baton['sub_hp'] = self.battle.poke_mgrs[idx].sub_hp

                    baton_cond = [key for key, val in self.battle.poke_mgrs[idx].count.items() if key.is_baton and val]
                    for cond in baton_cond:
                        baton[cond] = self.battle.poke_mgrs[idx].count[cond]

            self.switch_pokemon(idx, command=switch_commands[idx], baton=baton)
            Uturned = True
            switch_commands[idx] = Command.NONE  # コマンド破棄

        if not any(self.breakpoint):
            if not ejectbutton_triggered and not Uturned:
                # だっしゅつパック判定 (わざ発動後)
                if (idxes := [i for i in self.speed_order if self.is_ejectpack_triggered(i)]):
                    self.breakpoint[idxes[0]] = f"ejectpack_move_{idx}"
                    self.battle.pokemons[idxes[0]].item.consume()
                    for i in idxes:
                        self.battle.poke_mgrs[i].rank_dropped = False

        # だっしゅつパックによる交代
        if (s := f"ejectpack_move_{idx}") in self.breakpoint:
            idx = self.breakpoint.index(s)
            self.switch_pokemon(idx, command=switch_commands[idx])
            switch_commands[idx] = Command.NONE  # コマンド破棄

        if not any(self.breakpoint):
            # あばれる状態の判定
            attacker_mgr.process_tagged_move(move, 'rage')

            # のどスプレー判定
            if self.battle.pokemons[idx].hp and self.battle.pokemons[idx].item.name == 'のどスプレー':
                attacker_mgr.activate_item(move)

            # 即時アイテムの判定
            if self.battle.pokemons[idx].item.immediate and self.battle.pokemons[idx].hp:
                attacker_mgr.activate_item()

            # 後手が瀕死なら中断
            if self.battle.pokemons[dfn].hp == 0:
                break

    if not any(self.breakpoint):
        if self.battle.winner() is not None:  # 勝敗判定
            return

        self.end_turn()  # ターン終了処理

        if self.battle.winner() is not None:  # 勝敗判定
            return

        # だっしゅつパック判定
        if (idxes := [i for i in self.speed_order if self.is_ejectpack_triggered(i)]):
            self.breakpoint[idxes[0]] = 'ejectpack_end'
            self.battle.pokemons[idxes[0]].item.consume()
            for i in idxes:
                self.battle.poke_mgrs[i].rank_dropped = False

    # だっしゅつパックによる交代
    if (s := 'ejectpack_end') in self.breakpoint:
        idx = self.breakpoint.index(s)
        self.switch_pokemon(idx, command=switch_commands[idx])
        switch_commands[idx] = Command.NONE  # コマンド破棄

    # 死に出し処理
    while self.battle.winner() is None:  # 勝敗判定
        idxes = []

        # 交代するプレイヤーを決定
        if not any(self.breakpoint):
            idxes = [i for i in range(2) if self.battle.pokemons[i].hp == 0]
            for i in idxes:
                self.breakpoint[i] = 'fainting'
        else:
            idxes = [i for i in range(2) if self.breakpoint[i] == 'fainting']

        if not idxes:
            break

        # 交代
        for idx in idxes:
            self.switch_pokemon(idx, command=switch_commands[idx], landing=False)
            switch_commands[idx] = Command.NONE  # コマンド破棄

        # 両者が死に出しした場合は、素早さ順に処理する
        if len(idxes) > 1:
            idxes = self.speed_order

        # 着地処理
        for idx in idxes:
            self.land(idx)

    # コマンドを記録
    self.battle.logger.append(CommandLog(self.battle.turn, self.command, self.switch_history))
