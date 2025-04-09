from __future__ import annotations

from copy import deepcopy
import warnings

from pokebot.sv.pokeDB import PokeDB


class Move:
    """ポケモンの技を表現するクラス"""

    def __init__(self, name: str = 'テラバースト', pp: int = None, observed: bool = False):
        """
        Parameters
        ----------
        name : str, optional
            技名, by default 'テラバースト'
        pp : int, optional
            技のPP, by default None
        """

        if name and name not in PokeDB.moves:
            warnings.warn(f"{name} is not in PokeDB.moves")
            return

        self.name = name                                            # 技名
        self._org_pp = pp if pp else PokeDB.moves[name]['pp']       # 元のPP
        self.observed = observed                                    # 観測されたらTrue

        self.pp = self._org_pp                                      # PP
        self.type = PokeDB.moves[name]['type']                      # タイプ
        self.cls = PokeDB.moves[name]['class']                      # 分類 phy/spe/sta
        self.power = PokeDB.moves[name]['power']                    # 威力
        self.hit = PokeDB.moves[name]['hit']                        # 命中率
        self.priority = PokeDB.move_to_priority[name] if \
            name in PokeDB.move_to_priority else 0                     # 優先度

    def game_reset(self):
        """試合開始前の状態に初期化"""
        self.pp = self._org_pp
        self.observed = False

    def dump(self) -> dict:
        return deepcopy(vars(self))

    def load(self, d: dict):
        self.__dict__ |= d

    def __str__(self):
        return self.name

    def __eq__(self, v: str | Move):
        return self.name == v if type(v) is str else self.name == v.name

    def __ne__(self, v: str | Move):
        return self.name != v if type(v) is str else self.name != v.name

    def add_pp(self, v: int):
        self.pp = max(0, min(self._org_pp, self.pp + v))
