from .player import Player


class UCTSPlayer(Player):
    """UCTSに基づいて勝率が最大となる行動をとる"""

    def __init__(self, n_search: int = 1000):
        super().__init__()
