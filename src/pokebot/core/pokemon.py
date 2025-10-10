from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Gender, Ailment, Stat
from pokebot.common.constants import NATURE_MODIFIER
import pokebot.common.utils as ut

from pokebot.core.events import Event, EventContext
from pokebot.data.registry import PokemonData

from .ability import Ability
from .item import Item
from .move import Move
from .active_status import ActiveStatus


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

        self.is_selected: bool = False
        self.sleep_count: int
        self.ailment: Ailment

        self.active_status: ActiveStatus = ActiveStatus(self)

        self.update_stats()
        self.hp: int = self.max_hp

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new, keys_to_deepcopy=['ability', 'item', 'moves'])
        return new

    def __str__(self):
        return self.name

    def switch_in(self, battle: Battle):
        self.observed = True
        self.ability.register_handlers(battle)
        self.item.register_handlers(battle)
        battle.add_turn_log(self, f"{self.name} 入場")

    def switch_out(self, battle: Battle):
        self.ability.unregister_handlers(battle)
        self.item.unregister_handlers(battle)
        battle.add_turn_log(self, f"{self.name} {'退場' if self.hp else '瀕死'}")

    @property
    def name(self):
        return self.data.name

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

    def show(self, sep: str = '\n\t'):
        s = f"{self.name}{sep}"
        s += f"HP {self.hp}/{self.stats[0]} ({self.hp_ratio*100:.0f}%){sep}"
        s += f"{self._nature}{sep}"
        s += f"{self.ability}{sep}"
        s += f"{self.item.name or 'No item'}{sep}"
        if self._terastal:
            s += f"{self._terastal}T{sep}"
        else:
            s += f"No terastal{sep}"
        for st, ef in zip(self._stats, self._effort):
            s += f"{st}({ef})-" if ef else f"{st}-"
        s = s[:-1] + sep
        s += "/".join(move.name for move in self.moves)
        print(s)

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

    def modify_hp(self, battle: Battle, v: int) -> bool:
        old = self.hp
        self.hp = max(0, min(self.max_hp, old + v))
        diff = self.hp - old
        if diff:
            battle.add_turn_log(self, f"HP {'+' if diff >= 0 else ''}{diff}")
        return diff != 0

    def modify_rank(self, battle: Battle, stat: Stat, v: int, by_self: bool = True) -> bool:
        old = self.active_status.rank[stat.idx]
        self.active_status.rank[stat.idx] = max(-6, min(6, old + v))
        delta = self.active_status.rank[stat.idx] - old
        if delta:
            battle.add_turn_log(self, f"{stat}{'+' if delta >= 0 else ''}{delta}")
            battle.events.emit(Event.ON_MODIFY_RANK,
                               EventContext(self, value={"value": delta, "by_self": by_self}))
        return delta != 0

    def find_move(self, move: Move | str) -> Move | None:
        for mv in self.moves:
            if move in [mv, mv.name]:
                return mv

    def knows(self, move: Move | str) -> bool:
        return self.find_move(move) is not None

    def is_sleeping(self) -> bool:
        return self.ailment == Ailment.SLP or self.ability.name == "ぜったいねむり"
