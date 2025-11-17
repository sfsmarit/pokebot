from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle
    from pokebot.model.pokemon import Pokemon

import random

from pokebot.utils.enums import Command
import pokebot.utils.copy_utils as copyut


class Player:
    def __init__(self, name: str = ""):
        self.name = name

        self.team: list[Pokemon] = []
        self.n_game: int = 0
        self.n_won: int = 0
        self.rating: float = 1500

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return copyut.fast_copy(self, new, keys_to_deepcopy=["team"])

    def choose_selection_commands(self, battle: Battle) -> list[Command]:
        n = min(3, len(self.team))
        return random.sample(battle.get_available_selection_commands(self), n)

    def choose_action_command(self, battle: Battle) -> Command:
        return random.choice(battle.get_available_action_commands(self))

    def choose_switch_command(self, battle: Battle) -> Command:
        return random.choice(battle.get_available_switch_commands(self))
