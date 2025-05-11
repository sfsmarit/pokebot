from __future__ import annotations

from copy import deepcopy

import pokebot.common.utils as ut
from pokebot.core import PokeDB


class Item:
    """ポケモンのアイテムを表現するクラス"""

    def __init__(self, name: str = ''):
        if name and name not in PokeDB.item_data:
            print(f"{name} is not in PokeDB.item_data")
            name = ''

        self._name: str = name
        self.active: bool = True
        self.observed: bool = False

        self._throw_power: int = 0
        self._buff_type: str | None = None
        self._debuff_type: str | None = None
        self._power_correction: float = 1
        self._consumable: bool = False
        self._immediate: bool = False
        self._post_hit: bool = False

        self.set_base_info()

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new)
        return new

    def __str__(self):
        return self.name

    def init_game(self):
        """試合開始前の状態に初期化"""
        self.active = bool(self._name)
        self.observed = False

    def mask(self):
        """非公開情報を隠蔽"""
        if not self.observed:
            self.name = ''

    def dump(self) -> dict:
        return deepcopy(vars(self))

    def load(self, d: dict):
        self.__dict__ |= d

    def consume(self):
        self.active = False
        self.observed = True

    def set_base_info(self):
        if self._name in PokeDB.item_data:
            self._throw_power = PokeDB.item_data[self._name]['throw_power']
            self._buff_type = PokeDB.item_data[self._name]['buff_type']
            self._debuff_type = PokeDB.item_data[self._name]['debuff_type']
            self._power_correction = PokeDB.item_data[self._name]['power_correction']
            self._consumable = PokeDB.item_data[self._name]['consumable']
            self._immediate = PokeDB.item_data[self._name]['immediate']
            self._post_hit = PokeDB.item_data[self._name]['post_hit']

    @property
    def name(self) -> str:
        return self._name if self.active else ''

    @name.setter
    def name(self, name: str):
        self._name = name
        self.set_base_info()

    @property
    def name_lost(self) -> str:
        return '' if self.active else self._name

    @property
    def throw_power(self) -> int:
        return self._throw_power if self.active else 0

    @property
    def buff_type(self) -> str | None:
        return self._buff_type if self.active else ''

    @property
    def debuff_type(self) -> str | None:
        return self._debuff_type if self.active else ''

    @property
    def power_correction(self) -> float:
        return self._power_correction if self.active else 1

    @property
    def consumable(self) -> bool:
        return self._consumable if self.active else False

    @property
    def immediate(self) -> bool:
        return self._immediate if self.active else False

    @property
    def post_hit(self) -> bool:
        return self._post_hit if self.active else False
