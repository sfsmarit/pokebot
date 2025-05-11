from __future__ import annotations

from copy import deepcopy

import pokebot.common.utils as ut
from pokebot.core import PokeDB


class Ability:
    """ポケモンの特性を表現するクラス"""

    def __init__(self, name: str = ""):
        if name and name not in PokeDB.abilities:
            print(f"{name} is not in PokeDB.abilities")
            name = ""

        self._org_name: str = name
        self._name: str = name
        self.active: bool = True
        self.tags = []
        self.observed: bool = False
        self.count: int = 0

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new)
        return new

    def __str__(self):
        return self.name

    def set_base_info(self):
        for tag, val in PokeDB.ability_tag.items():
            if self._name in val:
                self.tags.append(tag)

    def init_game(self):
        """試合開始前の状態に初期化"""
        self.bench_reset()
        self.active = True
        self.observed = False

    def bench_reset(self):
        """控えに戻した状態にする"""
        self._name = self._org_name
        self.count = 0

        if self.org_name not in PokeDB.ability_tag['one_time']:
            self.active = True

    def mask(self):
        """非公開情報を隠蔽"""
        if not self.observed:
            self._org_name = ""

    def dump(self) -> dict:
        return deepcopy(vars(self))

    def load(self, d: dict):
        self.__dict__ |= d

    @property
    def org_name(self) -> str:
        return self._org_name

    @org_name.setter
    def org_name(self, name: str):
        self._org_name = name
        self.name = name

    @property
    def name(self) -> str:
        return self._name if self.active else ''

    @name.setter
    def name(self, name: str):
        self._name = name

    def swap(self, target: Ability):
        self.name, target.name = target.name, self.name
        self.observed = target.observed = True
