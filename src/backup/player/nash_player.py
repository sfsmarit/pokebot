from .player import Player


class NashPlayer(Player):
    """ナッシュ均衡戦略に従う"""

    def __init__(self, n_search: int = 1000):
        super().__init__()
