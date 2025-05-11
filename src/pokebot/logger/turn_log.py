from dataclasses import dataclass
from copy import deepcopy

from pokebot.common.types import PlayerIndex


@dataclass
class TurnLog:
    turn: int
    idx: PlayerIndex | int | None
    text: str

    def dump(self):
        return deepcopy(vars(self))
