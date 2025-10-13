from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot import Player

import time
from random import Random

from pokebot.common.enums import Command, Interrupt, Stat
from pokebot.logger import Logger, TurnLog, CommandLog

from .events import EventManager, Event, EventContext
from .pokedb import PokeDB
from .pokemon import Pokemon
from .move import Move

from .damage import DamageCalculator, DamageContext


class Battle:
    def __init__(self,
                 player1: Player,
                 player2: Player,
                 seed: int | None = None) -> None:

        self.player: list[Player] = [player1, player2]

        if seed is None:
            seed = int(time.time())

        self.init_game(seed)

    def init_game(self, seed: int):
        self.seed = seed

        self.random = Random(seed)
        self.events = EventManager(self)
        self.logger = Logger()
        self.damage_calculator: DamageCalculator = DamageCalculator(self.events)

        self._winner: Player | None = None
        self.interrupt: list[Interrupt] = [Interrupt.NONE] * 2
        self.scheduled_switch_commands: list[list[Command]] = [[], []]

        self.turn: int = -1
        self.selection_idxes: list[list[int]] = [[], []]
        self.actives: list[Pokemon] = [None] * 2  # type: ignore

    def init_turn(self):
        self.command: list[Command] = [Command.NONE] * 2
        self.already_switched: list[bool] = [False] * 2
        self.turn += 1

    def get_player_index(self, obj: Pokemon | Player) -> int:
        if isinstance(obj, Pokemon):
            return self.actives.index(obj)
        else:
            return self.player.index(obj)

    def foe(self, poke: Pokemon) -> Pokemon:
        return self.actives[(self.actives.index(poke)+1) % 2]

    def get_available_selection_commands(self, player: Player) -> list[Command]:
        return Command.selection_commands()[:len(player.team)]

    def get_available_switch_commands(self, player: Player) -> list[Command]:
        return [cmd for poke, cmd in zip(player.team, Command.switch_commands())
                if poke.is_selected and poke not in self.actives]

    def get_available_action_commands(self, player: Player) -> list[Command]:
        idx = self.player.index(player)
        n = len(self.actives[idx].moves)

        # 通常技
        commands = Command.move_commands()[:n]

        # テラスタル
        if player.can_use_terastal():
            commands += Command.terastal_commands()[:n]

        # わるあがき
        if not commands:
            commands = [Command.STRUGGLE]

        # 交代コマンド
        commands += self.get_available_switch_commands(player)

        return commands

    def get_turn_logs(self, turn: int | None = None) -> list[list[str]]:
        if turn is None:
            turn = self.turn
        return self.logger.get_turn_logs(turn)

    def write_log(self, obj: int | Pokemon | Player, text: str):
        if isinstance(obj, Pokemon):
            obj = self.actives.index(obj)
        elif not isinstance(obj, int):
            obj = self.player.index(obj)
        self.logger.append(TurnLog(self.turn, obj, text))

    def get_speed_order(self) -> list[int]:
        return [0, 1]

    def get_action_order(self) -> list[int]:
        return [0, 1]

    def selected_pokemons(self, player_idx: int) -> list[Pokemon]:
        return [self.player[player_idx].team[i] for i in self.selection_idxes[player_idx]]

    def TOD_score(self, player_idx: int, alpha: float = 1):
        n_alive, total_max_hp, total_hp = 0, 0, 0
        for poke in self.selected_pokemons(player_idx):
            total_max_hp += poke.max_hp
            total_hp += poke.hp
            if poke.hp:
                n_alive += 1
        return n_alive + alpha * total_hp / total_max_hp

    def winner(self) -> Player | None:
        if not self._winner:
            TOD_scores = [self.TOD_score(i) for i in range(2)]
            if 0 in TOD_scores:
                idx = TOD_scores.index(0)
                self._winner = self.player[not idx]
                self.write_log(not idx, "勝ち")
                self.write_log(idx, "負け")
        return self._winner

    def run_selection(self):
        for idx in range(2):
            # チーム番号を記録
            commands = self.player[idx].get_selection_commands(self)
            self.selection_idxes[idx] = [cmd.idx for cmd in commands]

            # 選出フラグを立てる
            for i in self.selection_idxes[idx]:
                self.player[idx].team[i].is_selected = True

    def run_move(self, player_idx: int, move: Move):
        source = self.actives[player_idx]
        foe = self.foe(source)

        move.register_handlers(self.events)

        # 技判定より前の処理
        self.events.emit(Event.ON_BEFORE_MOVE, EventContext(source))

        self.write_log(self.get_player_index(source), f"{move}")

        # 発動成功判定
        self.events.emit(Event.ON_TRY_MOVE, EventContext(source))

        # 命中判定
        pass

        source.field_status.executed_move = move

        # ダメージ計算
        damage = self.calc_damage(source, move)

        # ダメージ付与
        self.modify_hp(foe, -damage)

        # 技が命中したときの処理
        self.events.emit(Event.ON_HIT, EventContext(source))

        # 技によってダメージを与えたときの処理
        if damage:
            self.events.emit(Event.ON_DAMAGE, EventContext(source))

        move.unregister_handlers(self.events)

    def query_switch(self, player_idx: int) -> Pokemon:
        if self.scheduled_switch_commands[player_idx]:
            command = self.scheduled_switch_commands[player_idx].pop(0)
        else:
            command = self.player[player_idx].get_switch_command(self)
        return self.player[player_idx].team[command.idx]

    def get_move_from_command(self, player_idx: int, command: Command) -> Move:
        if command == Command.STRUGGLE:
            return PokeDB.create_move("わるあがき")
        elif command.is_zmove():
            return PokeDB.create_move("わるあがき")
        else:
            return self.actives[player_idx].moves[command.idx]

    def modify_hp(self, target: Pokemon, v: int):
        if v and (delta := target.modify_hp(v)):
            self.write_log(target, f"HP {'+' if delta >= 0 else ''}{delta} >> {target.hp}")

    def modify_stat(self, target: Pokemon, stat: Stat, v: int, by_foe: bool = False):
        if v and (delta := target.modify_stat(stat, v)):
            self.write_log(target, f"{stat}{'+' if delta >= 0 else ''}{delta}")
            self.events.emit(Event.ON_MODIFY_STAT,
                             EventContext(target, value=delta, by_foe=by_foe))

    def calc_damage(self,
                    attacker: Pokemon,
                    move: Move | str,
                    critical: bool = False,
                    self_harm: bool = False) -> int:
        return self.random.choice(
            self.calc_damages(attacker, move, critical, self_harm))

    def calc_damages(self,
                     attacker: Pokemon,
                     move: Move | str,
                     critical: bool = False,
                     self_harm: bool = False) -> list[int]:
        if isinstance(move, str):
            move = PokeDB.create_move(move)
        defender = attacker if self_harm else self.foe(attacker)
        dmg_ctx = DamageContext(critical, self_harm)
        return self.damage_calculator.single_hit_damages(
            attacker, defender, move, dmg_ctx)

    def has_interrupt(self) -> bool:
        return any(x != Interrupt.NONE for x in self.interrupt)

    def update_ejectpack_interrupt(self, flag: Interrupt):
        for idx in self.get_speed_order():
            if self.interrupt[idx] == Interrupt.EJECTPACK_REQUESTED:
                self.interrupt[idx] = flag
                return

    def run_switch(self, player_idx: int, new: Pokemon, emit_switch_in: bool = True):
        # 退場
        old = self.actives[player_idx]
        if old is not None:
            self.events.emit(Event.ON_SWITCH_OUT, EventContext(self.actives[player_idx]))
            old.switch_out(self.events)
            self.write_log(old, f"{old} {'退場' if old.hp else '瀕死'}")

        # 入場
        self.actives[player_idx] = new
        new.switch_in(self.events)
        self.write_log(new, f"{new} 入場")
        if emit_switch_in:
            self.events.emit(Event.ON_SWITCH_IN, EventContext(self.actives[player_idx]))

        # 割り込みフラグを破棄
        self.interrupt[player_idx] = Interrupt.NONE

        self.already_switched[player_idx] = True

    def run_initial_switch(self):
        # ポケモンを場に出す
        # 場に出たときの処理は両者の交代が完了したあとに行う
        for idx, player in enumerate(self.player):
            new = player.team[self.selection_idxes[idx][0]]
            self.run_switch(idx, new, emit_switch_in=False)

        # ポケモンが場に出たときの処理
        self.events.emit(Event.ON_SWITCH_IN)

    def run_interrupt_switch(self, flag: Interrupt):
        # 交代
        for idx in range(2):
            if self.interrupt[idx] == flag:
                self.run_switch(idx, self.query_switch(idx), emit_switch_in=False)

        # 場に出たときの処理
        for idx in self.get_speed_order():
            if self.interrupt[idx] == flag:
                self.events.emit(Event.ON_SWITCH_IN,
                                 EventContext(self.actives[idx]))

    def run_faint_switch(self):
        while self.winner() is None:
            if not self.has_interrupt():
                for i, poke in enumerate(self.actives):
                    if poke.hp == 0:
                        self.interrupt[i] = Interrupt.FAINTED

            # 交代を行うプレイヤー
            idxes = [i for i in range(2) if self.interrupt[i] == Interrupt.FAINTED]

            # 交代を行うプレイヤーがいなければ終了
            if not idxes:
                return

            # 瀕死による交代
            self.run_interrupt_switch(Interrupt.FAINTED)

    def advance_turn(self: Battle):
        if not self.has_interrupt():
            self.init_turn()

        if self.turn == 0:
            if not self.has_interrupt():
                # ポケモンを選出
                self.run_selection()

                # ポケモンを場に出す
                self.run_initial_switch()

                # だっしゅつパックによる割り込みフラグを更新
                self.update_ejectpack_interrupt(Interrupt.EJECTPACK_ON_START)

            # 割り込み
            self.run_interrupt_switch(Interrupt.EJECTPACK_ON_START)

            return

        if not self.has_interrupt():
            # 行動選択
            for idx, player in enumerate(self.player):
                self.command[idx] = player.get_action_command(self)

            # 行動順の更新
            pass

            # 行動前の処理
            self.events.emit(Event.ON_BEFORE_ACTION)

        # 行動: 交代
        for idx in self.get_action_order():
            if not self.has_interrupt():
                if self.command[idx].is_switch():
                    new = self.player[idx].team[self.command[idx].idx]
                    self.run_switch(idx, new)
                else:
                    self.write_log(idx, self.actives[idx].name)

                # だっしゅつパックによる割り込みフラグを更新
                self.update_ejectpack_interrupt(Interrupt.get_ejectpack_on_switch(idx))

            # だっしゅつパックによる交代
            self.run_interrupt_switch(Interrupt.get_ejectpack_on_switch(idx))

        # 行動: 技
        for idx in self.get_action_order():
            # このターンに交代済みなら行動不可
            if self.already_switched[idx]:
                continue

            # 技の発動
            move = self.get_move_from_command(idx, self.command[idx])
            self.run_move(idx, move)

            # だっしゅつボタンによる交代
            self.run_interrupt_switch(Interrupt.EJECTBUTTON)

            # 交代技による交代
            self.run_interrupt_switch(Interrupt.PIVOT)

            if not self.has_interrupt():
                # 交代技の後の処理
                self.events.emit(Event.ON_AFTER_PIVOT,
                                 EventContext(self.actives[idx]))

                # だっしゅつパックによる割り込みフラグを更新
                self.update_ejectpack_interrupt(Interrupt.get_ejectpack_on_after_move(idx))

            # だっしゅつパックによる交代
            self.run_interrupt_switch(Interrupt.get_ejectpack_on_after_move(idx))

        # ターン終了時の処理 (1)
        if not self.has_interrupt():
            self.events.emit(Event.ON_TURN_END_1)

        # ターン終了時の処理 (2)
        if not self.has_interrupt():
            self.events.emit(Event.ON_TURN_END_2)

        # ターン終了時の処理 (3)
        if not self.has_interrupt():
            self.events.emit(Event.ON_TURN_END_3)

        # ターン終了時の処理 (4)
        if not self.has_interrupt():
            self.events.emit(Event.ON_TURN_END_4)

            # だっしゅつパックによる割り込みフラグを更新
            self.update_ejectpack_interrupt(Interrupt.EJECTPACK_ON_TURN_END)

        # だっしゅつパックによる交代
        self.run_interrupt_switch(Interrupt.EJECTPACK_ON_TURN_END)

        # ターン終了時の処理 (5)
        if not self.has_interrupt():
            self.events.emit(Event.ON_TURN_END_5)

        self.run_interrupt_switch(Interrupt.EJECTPACK_ON_TURN_END)

        # 瀕死による交代
        self.run_faint_switch()
