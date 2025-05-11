from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..battle.battle import Battle

from pokebot.common.enums import GlobalField, SideField, Weather, Terrain
from pokebot.common.constants import WEATHER_STONE
from pokebot.common.types import PlayerIndex
import pokebot.common.utils as ut
from pokebot.logger import TurnLog


class FieldManager:
    def __init__(self, battle: Battle):
        self.battle: Battle = battle

        self.count: dict = {}

        self._weather: Weather
        self._terrain: Terrain
        self._wish_heal: list[int]

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new)
        return new

    def init_game(self):
        for x in GlobalField:
            self.count[x] = 0
        for x in SideField:
            self.count[x] = [0, 0]

        self._weather = Weather.NONE
        self._terrain = Terrain.NONE
        self._wish_heal = [0, 0]

    def _set_count(self,
                   field: GlobalField | SideField,
                   idx: PlayerIndex | None = None,
                   count: int = 0):
        if isinstance(field, GlobalField):
            self.count[field] = count
        else:
            self.count[field][idx] = count
        self.battle.logger.append(TurnLog(self.battle.turn, idx, f"{field} {idx} +{count}"))

    def set_weather(self,
                    weather: Weather,
                    idx: PlayerIndex,
                    count: int | None = None) -> bool:
        # 重ね掛け不可
        if self._weather == weather:
            return False

        self._weather = weather

        if count is None:
            count = 8 if self.battle.pokemon[idx].item == WEATHER_STONE[weather] else 5
        self._set_count(GlobalField.WEATHER, idx, count)

        # 特性の判定
        for i, poke in enumerate(self.battle.pokemon):
            if poke.ability.name == 'こだいかっせい':
                self.battle.poke_mgr[i].activate_ability()

        return True

    def set_terrain(self,
                    terrain: Terrain,
                    idx: PlayerIndex,
                    count: int | None = None) -> bool:

        # 重ね掛け不可
        if self._terrain == terrain:
            return False

        self._terrain = terrain

        if count is None:
            count = 8 if self.battle.pokemon[idx].item == "グランドコート" else 5
        self._set_count(GlobalField.TERRAIN, idx, count)

        # 特性の判定
        for i, poke in enumerate(self.battle.pokemon):
            if poke.ability.name == 'クォークチャージ':
                self.battle.poke_mgr[i].activate_ability()

        return True

    def set_field(self,
                  field: GlobalField | SideField,
                  idx: PlayerIndex | None = None,
                  count: int = 0) -> bool:

        # 重ね掛け不可
        if count and self.count[field]:
            return False

        match field:
            case SideField.WISH:
                if idx:
                    if count and self._wish_heal[idx] == 0:
                        # ねがいごと起動
                        self._wish_heal[idx] = int(self.battle.pokemon[idx].stats[0]/2)
                    elif count == 0 and self._wish_heal[idx]:
                        # ねがいごと終了
                        self.battle.poke_mgr[idx].add_hp(self._wish_heal[idx])
                        self._wish_heal[idx] = 0

        return True

    def add_count(self,
                  field: GlobalField | SideField,
                  idx: PlayerIndex | None = None,
                  v: int = 1) -> bool:
        if isinstance(field, GlobalField):
            count = self.count[field]
        else:
            count = self.count[field][idx]

        if (v < 0 and count == 0) or (v > 0 and count == field.max_count):
            return False

        self.set_field(field, idx, max(0, min(field.max_count, v + v)))
        return True

    def weather(self, perspective: PlayerIndex | None = None) -> Weather:
        active_abilities = [p.ability.name for p in self.battle.pokemon]
        if any(s in active_abilities for s in ['エアロック', 'ノーてんき']):
            return Weather.NONE
        if perspective is not None and \
            self.battle.pokemon[perspective].item.name == 'ばんのうがさ' and \
                self._weather in [Weather.SUNNY, Weather.RAINY]:
            return Weather.NONE
        return self._weather

    def terrain(self, perspective: PlayerIndex | None = None) -> Terrain:
        if perspective is not None and \
                self.battle.poke_mgr[perspective].is_floating():
            return Terrain.NONE
        return self._terrain
