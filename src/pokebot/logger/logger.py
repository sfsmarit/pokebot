from copy import deepcopy

from pokebot.common.types import PlayerIndex
import pokebot.common.utils as ut

from .command_log import CommandLog
from .turn_log import TurnLog
from .damage_log import DamageLog


class Logger:
    def __init__(self):
        self.turn_logs: list[TurnLog] = []
        self.command_logs: list[CommandLog] = []
        self.damage_logs: list[DamageLog] = []

    def clear(self):
        self.turn_logs.clear()
        self.command_logs.clear()
        self.damage_logs.clear()

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new)
        return new

    def get_turn_summary(self, turn: int, idx: PlayerIndex | int) -> str:
        logs = []
        for log in self.turn_logs:
            if log.turn == turn and log.idx in [idx, None]:
                logs.append(log.text)
        return ", ".join(logs)

    def get_damage_summary(self, turn: int, idx: PlayerIndex | int) -> list[str]:
        notes = []
        for log in self.damage_logs:
            if log.turn == turn and log.idx in [idx, None]:
                notes.append(log.notes)
        return notes

    def append(self, log: TurnLog | CommandLog | DamageLog):
        if isinstance(log, TurnLog):
            self.turn_logs.append(log)
        elif isinstance(log, CommandLog):
            self.command_logs.append(log)
        elif isinstance(log, DamageLog):
            self.damage_logs.append(log)

    def insert(self, i: int, log: TurnLog | CommandLog | DamageLog):
        if isinstance(log, TurnLog):
            self.turn_logs.insert(i, log)
        elif isinstance(log, CommandLog):
            self.command_logs.insert(i, log)
        elif isinstance(log, DamageLog):
            self.damage_logs.insert(i, log)
