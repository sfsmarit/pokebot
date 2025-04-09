from __future__ import annotations

from copy import deepcopy
import warnings

from pokebot.sv.pokeDB import PokeDB


class Ability:
    """ポケモンの特性を表現するクラス"""

    def __init__(self, name: str = ''):
        if name and name not in PokeDB.abilities:
            warnings.warn(f"{name} is not in PokeDB.abilities")
            name = ''

        self.org_name = name            # もとの特性
        self.game_reset()

    def game_reset(self):
        """試合開始前の状態に初期化"""
        self.bench_reset()
        self.active = True              # 特性が有効ならTrue
        self.observed = False           # 観測されたらTrue

    def bench_reset(self):
        """控えに戻した状態にする"""
        self._name = self._org_name     # 現在の特性
        self.count = 0

        if self.org_name not in PokeDB.category_to_abilities['one_time']:
            self.active = True

    def mask(self):
        """非公開情報を隠蔽"""
        if not self.observed:
            self._org_name = ''

    def dump(self) -> dict:
        return deepcopy(vars(self))

    def load(self, d: dict):
        self.__dict__ |= d

    @property
    def org_name(self):
        return self._org_name

    @property
    def name(self):
        return self._name if self.active else ''

    @property
    def name(self):
        return self._name if self.active else ''

    @property
    def immediate(self):
        return self._immediate if self.active else False

    @property
    def unreproducible(self):
        return self._unreproducible if self.active else False

    @property
    def protected(self):
        return self._protected if self.active else False

    @property
    def undeniable(self):
        return self._undeniable if self.active else False

    @org_name.setter
    def org_name(self, name: str | Ability):
        self._org_name = self._name = name

    @name.setter
    def name(self, name: str):
        self._name = name

        self.categories = []
        for category, abilities in PokeDB.category_to_abilities:
            if name in abilities:
                self.categories.append(category)

    def __str__(self):
        return self.name

    def __eq__(self, v: str | Ability):
        return self.name == v if type(v) is str else self.name == v.name

    def __ne__(self, v: str | Ability):
        return self.name != v if type(v) is str else self.name != v.name

    def swap(self, ability: Ability):
        self.name, ability.name = ability.name, self.name
        self.observed = ability.observed = True
