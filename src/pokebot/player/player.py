from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle, Pokemon

from pokebot.common.enums import Command, Phase
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

    def get_selection_command(self, battle: Battle) -> list[Command]:
        """ターン行動の方策関数"""
        return battle.get_available_command(self, Phase.SELECTION)[:3]

    def get_action_command(self, battle: Battle) -> Command:
        """ターン行動の方策関数"""
        return battle.get_available_command(self, Phase.ACTION)[0]
