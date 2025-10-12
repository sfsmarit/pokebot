from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot import Player

import time
from random import Random

from pokebot.common.enums import Command, Breakpoint
from pokebot.logger import Logger, TurnLog, CommandLog

from .events import EventManager, Event
from .pokedb import PokeDB
from .pokemon import Pokemon
from .move import Move

from . import battle_methods as methods


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

        self._winner: Player | None = None
        self.breakpoint: list[Breakpoint | None] = [None, None]
        self.scheduled_switch_commands: list[list[Command]] = [[], []]

        self.turn: int = -1
        self.selection_idxes: list[list[int]] = [[], []]
        self.actives: list[Pokemon] = [None, None]  # type: ignore

    def init_turn(self):
        self.command: list[Command] = [Command.NONE, Command.NONE]
        self.already_switched: list[bool] = [False, False]
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

    def add_turn_log(self, obj: int | Pokemon | Player, text: str):
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
                self.add_turn_log(not idx, "勝ち")
                self.add_turn_log(idx, "負け")
        return self._winner

    def advance_turn(self):
        return methods.advance_turn(self)

    def run_selection(self):
        for idx in range(2):
            # チーム番号を記録
            commands = self.player[idx].get_selection_commands(self)
            self.selection_idxes[idx] = [cmd.idx for cmd in commands]

            # 選出フラグを立てる
            for i in self.selection_idxes[idx]:
                self.player[idx].team[i].is_selected = True

    def run_switch(self, player_idx: int, new: Pokemon, emit_switch_in: bool = True):
        return methods.run_switch(self, player_idx, new, emit_switch_in)

    def run_initial_switch(self):
        return methods.run_initial_switch(self)

    def run_faint_switch(self):
        return methods.run_faint_switch(self)

    def run_move(self, player_idx: int, move: Move):
        return methods.run_move(self, player_idx, move)

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
