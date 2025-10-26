from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.player.player import Player

import pokebot.common.utils as ut
from .turn_log import TurnLog
from .command_log import CommandLog


class Logger:
    def __init__(self):
        self.turn_logs: list[TurnLog] = []
        self.command_logs: list[CommandLog] = []

    def clear(self):
        self.turn_logs.clear()
        self.command_logs.clear()

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return ut.fast_copy(self, new)

    def get_turn_logs(self, turn: int) -> list[list[str]]:
        logs = [[], []]
        for log in self.turn_logs:
            if log.turn != turn:
                continue
            for idx in log.player_idxes:
                logs[idx].append(log.text)
        return logs

    def append(self, log: TurnLog | CommandLog):
        if isinstance(log, TurnLog):
            self.turn_logs.append(log)
        elif isinstance(log, CommandLog):
            self.command_logs.append(log)

    def insert(self, pos: int, log: TurnLog | CommandLog):
        if isinstance(log, TurnLog):
            self.turn_logs.insert(pos, log)
        elif isinstance(log, CommandLog):
            self.command_logs.insert(pos, log)
