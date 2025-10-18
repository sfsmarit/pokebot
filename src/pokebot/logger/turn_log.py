from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.player.player import Player

from copy import deepcopy


class TurnLog:
    def __init__(self, turn: int, players: list[Player], text: str) -> None:
        self.turn: int = turn
        self.players: list[Player] = players
        self.text: str = text

    def dump(self):
        return deepcopy(vars(self))
