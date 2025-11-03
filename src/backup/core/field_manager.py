from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .battle import Battle

from pokebot.common.enums import GlobalField, SideField, Weather, Terrain
from pokebot.common.constants import WEATHER_STONE
from pokebot.common.types import PlayerIndex
import pokebot.common.utils as ut
from pokebot.logger import TurnLog


class FieldManager:
    """
    場の状態を管理するクラス
    """

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
        ut.fast_copy(self, new)
        return new

    def dump(self) -> dict:
        d: dict = ut.recursive_copy(vars(self))  # type: ignore
        del d['battle']
        return d

    def load(self, d: dict):
        self.__dict__ |= d

    def init_game(self):
        """試合開始前の状態に初期化する"""
        for x in GlobalField:
            self.count[x] = 0
        for x in SideField:
            self.count[x] = [0, 0]

        self._weather = Weather.NONE
        self._terrain = Terrain.NONE
        self._wish_heal = [0, 0]

    def _set_count(self,
                   field: GlobalField | SideField,
                   idx: PlayerIndex | int | None = None,
                   count: int = 0):
        """
        場のカウント(残りターン数)を設定する

        Parameters
        ----------
        field : GlobalField | SideField
            対象の場
        idx : PlayerIndex | int | None, optional
            変更を行うプレイヤー番号
        count : int, optional
            カウント, by default 0
        """
        if isinstance(field, GlobalField):
            self.count[field] = count
        else:
            self.count[field][idx] = count
        self.battle.logger.add(TurnLog(self.battle.turn, idx, f"{field} +{count}"))

    def set_weather(self,
                    weather: Weather,
                    idx: PlayerIndex | int,
                    count: int | None = None) -> bool:
        """
        天候を設定する

        Parameters
        ----------
        weather : Weather
            天候
        idx : PlayerIndex | int
            変更を行うプレイヤー番号
        count : int | None, optional
            カウント, by default None

        Returns
        -------
        bool
            設定できたらTrue
        """
        # 重ね掛け不可
        if self._weather == weather:
            return False

        self._weather = weather

        if weather == Weather.NONE:
            count = 0
        elif count is None:
            count = 8 if self.battle.pokemons[idx].item.name == WEATHER_STONE[weather] else 5
            self.battle.logger.add(TurnLog(self.battle.turn, idx, weather.value[0]))

        self._set_count(GlobalField.WEATHER, idx, count)

        # 特性の発動判定
        for i, poke in enumerate(self.battle.pokemons):
            if poke.ability.name == 'こだいかっせい':
                self.battle.poke_mgrs[i].activate_ability()

        return True

    def set_terrain(self,
                    terrain: Terrain,
                    idx: PlayerIndex | int,
                    count: int | None = None) -> bool:
        """
        フィールドを設定する

        Parameters
        ----------
        terrain : Terrain
            フィールド
        idx : PlayerIndex | int
            変更を行うプレイヤー番号
        count : int | None, optional
            カウント, by default None

        Returns
        -------
        bool
            設定できたらTrue
        """
        # 重ね掛け不可
        if self._terrain == terrain:
            return False

        self._terrain = terrain

        if terrain == Terrain.NONE:
            count = 0
        if count is None:
            count = 8 if self.battle.pokemons[idx].item.name == "グランドコート" else 5
            self.battle.logger.add(TurnLog(self.battle.turn, idx, terrain.value[0]))

        self._set_count(GlobalField.TERRAIN, idx, count)

        # 特性の発動判定
        for i, poke in enumerate(self.battle.pokemons):
            if poke.ability.name == 'クォークチャージ':
                self.battle.poke_mgrs[i].activate_ability()

        return True

    def set_field(self,
                  field: GlobalField | SideField,
                  idx: PlayerIndex | int | None = None,
                  count: int = 0) -> bool:
        """
        天候・フィールド以外の場を設定する

        Parameters
        ----------
        field : GlobalField | SideField
            場
        idx : PlayerIndex | int | None, optional
            変更を行うプレイヤー番号, by default None
        count : int, optional
            場のカウント, by default 0

        Returns
        -------
        bool
            設定できたらTrue
        """

        # 変動しない
        if (isinstance(field, GlobalField) and self.count[field] == count) or \
                (isinstance(field, SideField) and self.count[field][idx] == count):
            return False

        # 重ね掛け不可
        if count and \
            ((isinstance(field, GlobalField) and self.count[field]) or
             (isinstance(field, SideField) and self.count[field][idx])):
            return False

        match field:
            case SideField.WISH:
                if idx:
                    if count and self._wish_heal[idx] == 0:
                        # ねがいごと起動
                        self._wish_heal[idx] = int(self.battle.pokemons[idx].stats[0]/2)
                    elif count == 0 and self._wish_heal[idx]:
                        # ねがいごと終了
                        self.battle.poke_mgrs[idx].add_hp(self._wish_heal[idx])
                        self._wish_heal[idx] = 0

        return True

    def add_count(self,
                  field: GlobalField | SideField,
                  idx: PlayerIndex | int | None = None,
                  v: int = 1) -> bool:
        """
        場のカウント(残りターン)を加算する

        Parameters
        ----------
        field : GlobalField | SideField
            対象の場
        idx : PlayerIndex | int | None, optional
            変更を行うプレイヤー番号, by default None
        v : int, optional
            加算するカウント, by default 1

        Returns
        -------
        bool
            変更できたらTrue
        """
        if isinstance(field, GlobalField):
            current_count = self.count[field]
        else:
            current_count = self.count[field][idx]

        if (v < 0 and current_count == 0) or (v > 0 and current_count == field.max_count):
            return False

        self._set_count(field, idx, max(0, min(field.max_count, current_count + v)))
        return True

    def weather(self, perspective: PlayerIndex | int | None = None) -> Weather:
        """プレイヤー視点の天候を返す"""
        active_abilities = [p.ability.name for p in self.battle.pokemons]
        if any(s in active_abilities for s in ['エアロック', 'ノーてんき']):
            return Weather.NONE
        if perspective is not None and \
            self.battle.pokemons[perspective].item.name == 'ばんのうがさ' and \
                self._weather in [Weather.SUNNY, Weather.RAINY]:
            return Weather.NONE
        return self._weather

    def terrain(self, perspective: PlayerIndex | int | None = None) -> Terrain:
        """プレイヤー視点のフィールドを返す"""
        if perspective is not None and \
                self.battle.poke_mgrs[perspective].is_floating():
            return Terrain.NONE
        return self._terrain
