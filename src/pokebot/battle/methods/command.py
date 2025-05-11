from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.battle.battle import Battle

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Command, Phase
from pokebot.common.types import PlayerIndex
from pokebot.core import Move


def _to_command(self: Battle,
                idx: PlayerIndex,
                selection_idx: int | None,
                switch_idx: int | None,
                move: Move | None,
                terastal: bool) -> Command:

    poke = self.pokemon[idx]

    if selection_idx is not None:
        return Command.selection_commands()[selection_idx]

    if switch_idx is not None:
        return Command.switch_commands()[switch_idx]

    if move and (move := poke.find_move(move)):
        move_idx = poke.moves.index(move)
        if terastal:
            return Command.terastal_commands()[move_idx]
        else:
            return Command.move_commands()[move_idx]

    return Command.NONE


def _command_to_str(self: Battle,
                    idx: PlayerIndex,
                    command: Command) -> str:
    match command.value[0]:
        case "SELECT":
            return f"選出 {self.player[idx].team[command.value[1]].name}"
        case "SWITCH":
            return f"交代 -> {self.player[idx].team[command.value[1]].name}"
        case "MOVE":
            return self.pokemon[idx].moves[command.value[1]].name
        case "TERASTAL":
            return f"T{self.pokemon[idx].moves[command.value[1]].name}"
        case "MEGAEVOL":
            return f"M{self.pokemon[idx].moves[command.value[1]].name}"
        case "STRUGGLE":
            return "わるあがき"
        case "FORCED":
            return "命令不可"
        case "SKIP":
            return "行動スキップ"
        case _:
            return command.value[0]


def _available_commands(self: Battle,
                        idx: PlayerIndex,
                        phase: Phase) -> list[Command]:
    commands = []

    match phase:
        case Phase.SELECTION:
            return Command.selection_commands()[:len(self.player[idx].team)]

        case Phase.BATTLE:
            if self.poke_mgr[idx].unresponsive_turn:
                return [Command.FORCED]

            # 技
            for move in self.pokemon[idx].moves:
                if self.poke_mgr[idx].can_choose_move(move)[0]:
                    commands.append(self.to_command(idx, move=move))
                # テラスタル
                if self.can_terastallize(idx):
                    commands.append(self.to_command(idx, move=move, terastal=True))

            # 交代
            if not self.poke_mgr[idx].is_caught():
                commands += [self.to_command(idx, switch_idx=i) for i in self.switchable_indexes(idx)]

            # わるあがき
            if not commands:
                commands = [Command.STRUGGLE]

        case Phase.SWITCH:
            commands += [self.to_command(idx, switch_idx=i) for i in self.switchable_indexes(idx)]

    if not commands:
        raise Exception(f"No available command for player {idx}")

    return commands
