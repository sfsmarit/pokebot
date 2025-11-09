from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.events import EventManager

from copy import deepcopy

from pokebot.utils.enums import Gender, Ailment, Stat, MoveCategory
from pokebot.utils.constants import NATURE_MODIFIER
import pokebot.utils.copy_utils as copyut

from pokebot.core.events import Event, EventContext
from pokebot.data.registry import PokemonData

from .ability import Ability
from .item import Item
from .move import Move
from .active_status import FieldStatus


def calc_hp(level, base, indiv, effort):
    return ((base*2 + indiv + effort//4) * level) // 100 + level + 10


def calc_stat(level, base, indiv, effort, nc):
    return int((((base*2 + indiv + effort//4) * level) // 100 + 5) * nc)


class Pokemon:
    def __init__(self, data: PokemonData):
        self.data: PokemonData = data
        self.observed: bool

        self.gender: Gender = Gender.NONE
        self._level: int = 50
        self._nature: str = "まじめ"
        self.ability: Ability = None  # type: ignore
        self.item: Item = None  # type: ignore
        self.moves: list[Move] = []
        self._indiv: list[int] = [31]*6
        self._effort: list[int] = [0]*6
        self._stats: list[int] = [100]*6
        self._terastal: str = ""
        self.is_terastallized: bool = False

        self.sleep_count: int
        self.ailment: Ailment

        self.field_status: FieldStatus = FieldStatus()

        self.update_stats()
        self.hp: int = self.max_hp

        self.added_types: list[str] = []
        self.lost_types: list[str] = []

    def __str__(self):
        sep = '\n\t'
        s = f"{self.name}{sep}"
        s += f"HP {self.hp}/{self.max_hp} ({self.hp_ratio*100:.0f}%){sep}"
        s += f"{self._nature}{sep}"
        s += f"{self.ability.name}{sep}"
        s += f"{self.item.name or 'No item'}{sep}"
        if self._terastal:
            s += f"{self._terastal}T{sep}"
        else:
            s += f"No terastal{sep}"
        for st, ef in zip(self._stats, self._effort):
            s += f"{st}({ef})-" if ef else f"{st}-"
        s = s[:-1] + sep
        s += "/".join(move.name for move in self.moves)
        return s

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        copyut.fast_copy(self, new, keys_to_deepcopy=['ability', 'item', 'moves', 'field_status'])
        return new

    def dump(self) -> dict:
        return {
            "name": self.data.name,
            "gender": self.gender.name,
            "level": self._level,
            "nature": self._nature,
            "ability": self.ability.data.name,
            "item": self.item.data.name,
            "moves": [move.data.name for move in self.moves],
            "indiv": self._indiv,
            "effort": self._effort,
            "terastal": self._terastal,
        }

    def switch_in(self, events: EventManager):
        self.observed = True
        if self.ability.active:
            self.ability.register_handlers(events, self)
        if self.item.active:
            self.item.register_handlers(events, self)

    def switch_out(self, events: EventManager):
        self.ability.unregister_handlers(events, self)
        self.item.unregister_handlers(events, self)

    @property
    def name(self):
        return self.data.name

    @property
    def types(self) -> list[str]:
        if self.terastal:
            if self.terastal == 'ステラ':
                return self.data.types.copy()
            else:
                return [self.terastal]
        else:
            if self.name == 'アルセウス':
                # TODO アルセウスのタイプ変化
                return ["ノーマル"]
            else:
                return [t for t in self.data.types if t not in
                        self.lost_types + self.added_types] + self.added_types

    @property
    def max_hp(self) -> int:
        return self.stats[0]

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp

    @property
    def level(self) -> int:
        return self._level

    @level.setter
    def level(self, level: int):
        self._level = level
        self.update_stats()

    @property
    def weight(self) -> float:
        w = self.data.weight
        match self.ability.name:
            case 'ライトメタル':
                w = int(w*0.5*10)/10
            case 'ヘヴィメタル':
                w *= 2
        if self.item.name == 'かるいし':
            w = int(w*0.5*10)/10
        return w

    @property
    def nature(self) -> str:
        return self._nature

    @nature.setter
    def nature(self, nature: str):
        self._nature = nature
        self.update_stats()

    @property
    def terastal(self) -> str | None:
        return self._terastal if self.is_terastallized else None

    @terastal.setter
    def terastal(self, type: str):
        self._terastal = type

    def can_terastallize(self) -> bool:
        return not self.is_terastallized and self._terastal is not None

    def terastallize(self) -> bool:
        self.is_terastallized = self.can_terastallize()
        return self.is_terastallized

    @property
    def stats(self) -> list[int]:
        return self._stats.copy()

    @stats.setter
    def stats(self, stats: list[int]):
        nc = NATURE_MODIFIER[self._nature]
        efforts_50 = [0] + [4+8*i for i in range(32)]

        for i in range(6):
            for eff in efforts_50:
                if i == 0:
                    v = calc_hp(self._level, self.data.base[i], self._indiv[i], self._effort[i])
                else:
                    v = calc_stat(self._level, self.data.base[i], self._indiv[i], self._effort[i], nc)
                if v == stats[i]:
                    self._effort[i] = eff
                    self._stats[i] = v
                    break

    @property
    def base(self) -> list[int]:
        return self.data.base.copy()

    @base.setter
    def base(self, base: list[int]):
        self.data.base = base
        self.update_stats()

    @property
    def indiv(self) -> list[int]:
        return self._indiv.copy()

    @indiv.setter
    def indiv(self, indiv: list[int]):
        self._indiv = indiv
        self.update_stats()

    @property
    def effort(self) -> list[int]:
        return self._effort.copy()

    @effort.setter
    def effort(self, effort: list[int]):
        self._effort = effort
        self.update_stats()

    def update_stats(self, keep_damage: bool = False):
        if keep_damage:
            damage = self._stats[0] - self.hp

        self._stats[0] = calc_hp(self._level, self.data.base[0], self._indiv[0], self._effort[0])
        for i in range(1, 6):
            self._stats[i] = calc_stat(self._level, self.data.base[i], self._indiv[i], self._effort[i], NATURE_MODIFIER[self._nature][i])

        if keep_damage:
            self.hp = self.hp - damage

    def set_stats(self, idx: int, value: int) -> bool:
        nc = NATURE_MODIFIER[self._nature]
        efforts_50 = [0] + [4+8*i for i in range(32)]

        for eff in efforts_50:
            if idx == 0:
                v = calc_hp(self._level, self.data.base[0], self._indiv[0], eff)
            else:
                v = calc_stat(self._level, self.data.base[idx], self._indiv[idx], eff, nc[idx])
            if v == value:
                self._effort[idx] = eff
                self._stats[idx] = v
                return True

        return False

    def set_effort(self, idx: int, value: int):
        self._effort[idx] = value
        self.update_stats()

    def modify_hp(self, v: int) -> int:
        old = self.hp
        self.hp = max(0, min(self.max_hp, old + v))
        return self.hp - old

    def modify_stat(self, stat: Stat, v: int) -> int:
        old = self.field_status.rank[stat.idx]
        self.field_status.rank[stat.idx] = max(-6, min(6, old + v))
        return self.field_status.rank[stat.idx] - old

    def find_move(self, move: Move | str) -> Move | None:
        for mv in self.moves:
            if move in [mv, mv.name]:
                return mv

    def knows(self, move: Move | str) -> bool:
        return self.find_move(move) is not None

    def floating(self, events: EventManager) -> bool:
        return False

    def trapped(self, events: EventManager) -> bool:
        self.field_status._trapped = False
        # self.field_status._trapped |= self.field_status.count[Condition.SWITCH_BLOCK] > 0
        # self.field_status._trapped |= self.field_status.count[Condition.BIND] > 0
        events.emit(Event.ON_CHECK_TRAP)
        self.field_status._trapped &= "ゴースト" not in self.types
        return self.field_status._trapped

    def effective_move_type(self, move: Move, events: EventManager) -> str:
        events.emit(Event.ON_CHECK_MOVE_TYPE,
                    ctx=EventContext(self, move))
        return move._type

    def effective_move_category(self, move: Move, events: EventManager) -> MoveCategory:
        events.emit(Event.ON_CHECK_MOVE_CATEGORY,
                    ctx=EventContext(self, move))
        return move._category
