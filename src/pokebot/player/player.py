from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle, Pokemon

import random

from pokebot.common.enums import Command
import pokebot.common.utils as ut


class Player:
    def __init__(self):
        self.team: list[Pokemon] = []
        self.n_game: int = 0
        self.n_won: int = 0
        self.rating: float = 1500

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new, keys_to_deepcopy=["team"])
        return new

    def get_selection_commands(self, battle: Battle) -> list[Command]:
        n = min(3, len(self.team))
        return random.sample(battle.get_available_selection_commands(self), n)

    def get_action_command(self, battle: Battle) -> Command:
        return random.choice(battle.get_available_action_commands(self))

    def get_switch_command(self, battle: Battle) -> Command:
        return random.choice(battle.get_available_switch_commands(self))

    def can_use_terastal(self) -> bool:
        return any(poke.can_terastallize() for poke in self.team if poke.is_selected)
