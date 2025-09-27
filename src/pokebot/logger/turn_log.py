from dataclasses import dataclass
from copy import deepcopy


@dataclass
class TurnLog:
    turn: int
    idx: int | None
    text: str

    def dump(self):
        return deepcopy(vars(self))
