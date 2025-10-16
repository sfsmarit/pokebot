from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.player.player import Player

from copy import deepcopy

import pokebot.common.utils as ut
from .command_log import CommandLog
from .turn_log import TurnLog


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
        ut.selective_deepcopy(self, new)
        return new

    def get_turn_logs(self, turn: int | None = None) -> dict[Player, list[str]]:
        logs = {}
        for log in self.turn_logs:
            if log.turn != turn:
                continue
            for player in log.players:
                logs.setdefault(player, []).append(log.text)
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
