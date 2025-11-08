from __future__ import annotations

from copy import deepcopy

import pokebot.common.utils as ut


class Ability:
    """
    ポケモンの特性を表現するクラス
    """

    def __init__(self, name: str = ""):
        self._org_name: str = name
        self._name: str = name

        self.flags: list[str] = []
        self.effects: list = []
        self.handlers: list = []

        self.observed: bool = False
        self.active: bool = True
        self.count: int = 0

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.fast_copy(self, new)
        return new

    def __str__(self):
        return self.name

    def set_base_info(self):
        if not self.name:
            return

        for tag, val in PokeDB.tagged_abilities.items():
            if self._name in val:
                self.flags.append(tag)

    def init_game(self):
        """試合開始前の状態に初期化"""
        self.bench_reset()
        self.active = True
        self.observed = False

    def bench_reset(self):
        """控えに戻した状態にする"""
        self._name = self.org_name
        self.set_base_info()
        self.count = 0
        if self.org_name not in PokeDB.tagged_abilities['one_time']:
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

    @property
    def name(self) -> str:
        return self._name if self.active else ''

    @name.setter
    def name(self, name: str):
        self._name = name
        self.set_base_info()
        self.count = 0
        self.active = True

    def swap(self, target: Ability):
        """特性を入れ替える"""
        self.name, target.name = target.name, self.name
        self.observed = target.observed = True  # 観測
