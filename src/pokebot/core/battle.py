from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot import Player

from pokebot.common.enums import Command
from pokebot.logger import Logger, TurnLog, CommandLog

from .events import EventManager, Event, EventContext
from .pokemon import Pokemon
from .move import Move


class Battle:
    def __init__(self, player1: Player, player2: Player) -> None:
        self.players: list[Player] = [player1, player2]

        self.events = EventManager(self)
        self.logger = Logger()

        self.turn: int = -1
        self.selection_idxes: list[list[int]] = [[], []]
        self.actives: list[Pokemon] = [None, None]  # type: ignore
        self.commands: list[Command] = [Command.NONE, Command.NONE]

    def idx(self, obj: Pokemon | Player) -> int:
        if isinstance(obj, Pokemon):
            return self.actives.index(obj)
        else:
            return self.players.index(obj)

    def foe(self, poke: Pokemon) -> Pokemon:
        return self.actives[(self.actives.index(poke)+1) % 2]

    def get_available_selection_commands(self, player: Player) -> list[Command]:
        return Command.selection_commands()[:len(player.team)]

    def get_available_switch_commands(self, player: Player) -> list[Command]:
        return [cmd for poke, cmd in zip(player.team, Command.switch_commands())
                if poke.is_selected and poke not in self.actives]

    def get_available_action_commands(self, player: Player) -> list[Command]:
        player_idx = self.players.index(player)
        n = len(self.actives[player_idx].moves)

        commands = Command.move_commands()[:n]
        if player.can_use_terastal():
            commands += Command.terastal_commands()[:n]
        commands += self.get_available_switch_commands(player)

        if not commands:
            commands = [Command.STRUGGLE]

        return commands

    def get_turn_logs(self, turn: int | None = None) -> list[list[str]]:
        if turn is None:
            turn = self.turn
        return self.logger.get_turn_logs(turn)

    def add_turn_log(self, id: int | Pokemon | Player, text: str):
        if isinstance(id, Pokemon):
            id = self.actives.index(id)
        elif not isinstance(id, int):
            id = self.players.index(id)
        self.logger.append(TurnLog(self.turn, id, text))

    def insert_turn_log(self, pos, id: int | Player | Pokemon, text: str):
        if isinstance(id, Pokemon):
            id = self.actives.index(id)
        elif not isinstance(id, int):
            id = self.players.index(id)
        self.logger.insert(pos, TurnLog(self.turn, id, text))

    # ----------------------------------------------------------------------
    #  ターン処理
    # ----------------------------------------------------------------------
    def advance_turn(self):
        self.turn += 1

        if self.turn == 0:
            self.start()
            return

        # 行動選択
        for i, player in enumerate(self.players):
            self.commands[i] = player.get_action_command(self)

        # 交代前の処理

        # 交代
        for i in self.get_action_order():
            if self.commands[i].is_switch():
                self.switch(i, self.players[i].team[self.commands[i].idx])
                continue

            # 技判定より前の処理
            self.events.emit(Event.ON_BEFORE_MOVE)

            if self.commands[i].is_move():
                move = self.actives[i].moves[self.commands[i].idx]
            else:
                continue

            # 発動成功判定
            self.events.emit(Event.ON_TRY_MOVE)

            # 命中判定
            pass

            # 発動
            self.run_move(move, self.actives[i])

        # ターン終了
        self.events.emit(Event.ON_TURN_END)

        if True:
            # 試合終了
            self.events.emit(Event.ON_END)

    def start(self):
        # プレイヤーから選出コマンドを取得
        for i, player in enumerate(self.players):
            self.selection_idxes[i] = [cmd.idx for cmd in player.get_selection_commands(self)]

        # ポケモンを場に出す
        for i, player in enumerate(self.players):
            self.actives[i] = player.team[self.selection_idxes[i][0]]
            self.actives[i].switch_in(self)

        # 交代時イベントの発火
        self.events.emit(Event.ON_SWITCH_IN)

    def get_action_order(self) -> list[int]:
        return [0, 1]

    def switch(self, player_idx: int, new: Pokemon):
        # 退場
        old = self.actives[player_idx]
        if old is not None:
            self.events.emit(Event.ON_SWITCH_OUT,
                             EventContext(self.actives[player_idx]))
            old.switch_out(self)

        # 入場
        self.actives[player_idx] = new
        new.switch_in(self)
        self.events.emit(Event.ON_SWITCH_IN,
                         EventContext(self.actives[player_idx]))

    def run_move(self, move: Move, source: Pokemon):
        move.register_handlers(self)

        self.add_turn_log(self.idx(source), f"{move}")

        self.events.emit(Event.ON_TRY_MOVE)

        source.active_status.executed_move = move

        # ダメージ計算
        damage = move.data.power

        # ダメージ付与
        self.foe(source).modify_hp(self, -damage)

        self.events.emit(Event.ON_HIT, EventContext(source))
        self.events.emit(Event.ON_DAMAGE, EventContext(source))
