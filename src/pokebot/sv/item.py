from __future__ import annotations

from copy import deepcopy
import warnings

from pokebot.sv.pokeDB import PokeDB


class Item:
    """ポケモンのアイテムを表現するクラス"""

    def __init__(self, name: str = ''):
        if name and name not in PokeDB.item_data:
            warnings.warn(f"{name} is not in PokeDB.item_data")
            name = ''

        self.name = name
        self.game_reset()

    def game_reset(self):
        """試合開始前の状態に初期化"""
        self.active = bool(self._name)       # 所持されていればTrue
        self.observed = False               # 観測されたらTrue

    def mask(self):
        """非公開情報を隠蔽"""
        if not self.observed:
            self.name = ''

    def dump(self) -> dict:
        return deepcopy(vars(self))

    def load(self, d: dict):
        self.__dict__ |= d

    def consume(self):
        self.item.active = False
        self.item.observed = True  # 観測

    @property
    def name(self):
        return self._name if self.active else ''

    @name.setter
    def name(self, name: str):
        self._name = name
        if name in PokeDB.item_data:
            self._throw_power = PokeDB.item_data[name]['throw_power']
            self._buff_type = PokeDB.item_data[name]['buff_type']
            self._debuff_type = PokeDB.item_data[name]['debuff_type']
            self._power_correction = PokeDB.item_data[name]['power_correction']
            self._consumable = PokeDB.item_data[name]['consumable']
            self._immediate = PokeDB.item_data[name]['immediate']
        else:
            self._throw_power = 0
            self._buff_type = None
            self._debuff_type = None
            self._power_correction = 1
            self._consumable = False
            self._immediate = False

    @property
    def name_lost(self):
        return '' if self.active else self._name

    @property
    def throw_power(self):
        return self._throw_power if self.active else 0

    @property
    def buff_type(self):
        return self._buff_type if self.active else ''

    @property
    def debuff_type(self):
        return self._debuff_type if self.active else ''

    @property
    def power_correction(self):
        return self._power_correction if self.active else 1

    @property
    def consumable(self):
        return self._consumable if self.active else False

    @property
    def immediate(self):
        return self._immediate if self.active else False

    def __str__(self):
        return self.name

    def __eq__(self, v: str | Item):
        return self.name == v if type(v) is str else self.name == v.name

    def __ne__(self, v: str | Item):
        return self.name != v if type(v) is str else self.name != v.name
