from .player import Player


class MCTSPlayer(Player):
    """MCTSに基づいて勝率が最大となる行動をとる"""

    def __init__(self, n_search: int = 1000):
        super().__init__()
