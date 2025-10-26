from copy import deepcopy


class TurnLog:
    def __init__(self, turn: int, player_idxes: list[int], text: str) -> None:
        self.turn: int = turn
        self.player_idxes: list[int] = player_idxes
        self.text: str = text

    def dump(self):
        return deepcopy(vars(self))
