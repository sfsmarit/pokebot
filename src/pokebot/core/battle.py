from __future__ import annotations
from pokebot.player import Player

from pokebot.common.enums import Phase, Command
from pokebot.logger import Logger, TurnLog, CommandLog

from .events.events import EventManager, Event
from .pokemon import Pokemon
from .move import Move


class Battle:
    def __init__(self, player1: Player, player2: Player) -> None:
        self.players: list[Player] = [player1, player2]

        self.events = EventManager()
        self.logger = Logger()

        self.turn: int = -1
        self.phase: Phase = Phase.NONE
        self.selection_idxes: list[list[int]] = [[], []]
        self.actives: list[Pokemon] = [None, None]  # type: ignore
        self.commands: list[Command] = [Command.NONE, Command.NONE]

    def idx(self, obj: Player | Pokemon) -> int:
        if isinstance(obj, Player):
            return self.players.index(obj)
        else:
            return self.actives.index(obj)

    def foe(self, poke: Pokemon) -> Pokemon:
        return self.actives[(self.actives.index(poke)+1) % 2]

    def get_available_command(self, player: Player, phase: Phase = Phase.NONE) -> list[Command]:
        commands = []
        match phase:
            case Phase.SELECTION:
                commands += Command.selection_commands()[:len(player.team)]
            case Phase.ACTION:
                commands += Command.move_commands()[:len(player.team)]
            case _:
                commands.append(Command.NONE)
        return commands

    def get_turn_logs(self, turn: int | None = None) -> list[list[str]]:
        if turn is None:
            turn = self.turn
        return self.logger.get_turn_logs(turn)

    def add_turn_log(self, id: int | Player | Pokemon, text: str):
        if isinstance(id, Player):
            id = self.players.index(id)
        elif isinstance(id, Pokemon):
            id = self.actives.index(id)
        self.logger.append(TurnLog(self.turn, id, text))

    def insert_turn_log(self, pos, id: int | Player | Pokemon, text: str):
        if isinstance(id, Player):
            id = self.players.index(id)
        elif isinstance(id, Pokemon):
            id = self.actives.index(id)
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

        # 行動前処理
        self.before_move()

        for i, source in enumerate(self.actives):
            self.events.emit(Event.ON_TRY_MOVE, self)
            move = source.moves[self.commands[i].idx]
            self.run_move(move, source)

        # ターン終了
        for source in self.actives:
            self.events.emit(Event.ON_TURN_END, self, source)

        if True:
            # 試合終了
            self.events.emit(Event.ON_END, self)

    def start(self):
        # プレイヤーから選出コマンドを取得
        for i, player in enumerate(self.players):
            self.selection_idxes[i] = [cmd.idx for cmd in player.get_selection_command(self)]

        # ポケモンを場に出す
        for i, player in enumerate(self.players):
            self.actives[i] = player.team[self.selection_idxes[i][0]]
            self.actives[i].enter(self)

        # 交代時イベントの発火
        for source in self.actives:
            self.events.emit(Event.ON_SWITCH_IN, self, source)

    def before_move(self):
        self.events.emit(Event.ON_BEFORE_MOVE, self)

        for i, cmd in enumerate(self.commands):
            if cmd.is_switch():
                self.actives[i].

    def switch(self, )

    def run_move(self, move: Move, source: Pokemon):
        move.register_handlers(self)

        self.add_turn_log(self.idx(source), f"{move}")

        self.events.emit(Event.ON_TRY_MOVE)

        source.active_status.executed_move = move

        # ダメージ計算
        damage = move.data.power

        # ダメージ付与
        self.foe(source).modify_hp(self, -damage)

        self.events.emit(Event.ON_HIT, battle=self, source=source)
        self.events.emit(Event.ON_DAMAGE, battle=self, source=source)
