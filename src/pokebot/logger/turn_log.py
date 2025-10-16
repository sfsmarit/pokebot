from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.player.player import Player

from dataclasses import dataclass, field
from copy import deepcopy


@dataclass
class TurnLog:
    turn: int
    players: list[Player]
    text: str

    def dump(self):
        return deepcopy(vars(self))
