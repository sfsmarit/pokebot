from __future__ import annotations
from pokebot.player import Player

from pokebot.common.enums import Event, Phase, Command
from pokebot.logger import Logger, TurnLog, CommandLog

from .event import EventManager
from .pokemon import Pokemon
from .move import Move


class Battle:
    def __init__(self, player1: Player, player2: Player) -> None:
        self.players: list[Player] = [player1, player2]

        self.events = EventManager()
        self.logger = Logger()

        self.turn: int = -1
        self.phase: Phase = Phase.NONE
        self.actives: list[Pokemon] = [None, None]  # type: ignore
        self.commands: list[Command] = [Command.NONE, Command.NONE]

    def advance_turn(self):
        self.turn += 1

        if self.turn == 0:
            # 場に出す
            for i, player in enumerate(self.players):
                commands = player.get_selection_command(self)
                self.actives[i] = player.team[commands[0].idx]
                self.actives[i].enter(self)

            # 交代イベント発火
            for user in self.actives:
                self.events.emit(Event.ON_SWITCH_IN, self, user)

            return

        # 行動選択
        for i, player in enumerate(self.players):
            self.commands[i] = player.get_action_command(self)

        # 行動前処理
        self.events.emit(Event.ON_BEFORE_MOVE, self)

        self.events.emit(Event.ON_TRY_MOVE, self)

        for user in self.actives:
            target = self.foe(user)
            move = user.moves[0]
            user.try_use_move(self, move, target)

        # ターン終了
        for user in self.actives:
            self.events.emit(Event.ON_TURN_END, self, user)

        if True:
            # 試合終了
            self.events.emit(Event.ON_END, self)

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

    def run_move(self, move: Move, user: Pokemon, target: Pokemon):
        move.register_handlers(self)

        # ダメージ計算
        damage = move.data.power

        self.events.emit(Event.ON_TRY_MOVE)

        # ダメージ付与
        target.modify_hp(self, -damage)

        self.events.emit(Event.ON_HIT, battle=self, user=user)
        self.events.emit(Event.ON_DAMAGE, battle=self, user=user)

    def add_turn_log(self, idx: int, text: str):
        self.logger.append(TurnLog(self.turn, idx, text))

    def insert_turn_log(self, pos, idx: int, text: str):
        self.logger.insert(pos, TurnLog(self.turn, idx, text))
