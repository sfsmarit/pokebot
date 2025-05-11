from dataclasses import dataclass
from copy import deepcopy

from pokebot.common.enums import Command


@dataclass
class CommandLog:
    turn: int
    command: list[Command]
    switch_commands: list[list[Command]]

    def dump(self):
        d = deepcopy(vars(self))

        for i, cmd in enumerate(d["command"]):
            d["command"][i] = cmd.value

        for i, commands in enumerate(d["switch_commands"]):
            d["switch_commands"][i] = [cmd.value for cmd in commands]

        return d
