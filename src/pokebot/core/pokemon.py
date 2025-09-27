from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.enums import Gender, Ailment
from pokebot.common.constants import NATURE_MODIFIER
import pokebot.common.utils as ut

from pokebot.data.registry import PokemonData
from pokebot.data import ABILITY, ITEM

from .ability import Ability
from .item import Item
from .move import Move
from .active_status import ActiveStatus


class Pokemon:
    def __init__(self, data: PokemonData):
        self.data: PokemonData = data
        self.gender: Gender = Gender.NONE
        self._level: int = 50
        self._nature: str = "まじめ"
        self.ability: Ability = Ability(ABILITY[""])
        self.item: Item = Item(ITEM[""])
        self.moves: list[Move] = []
        self._indiv: list[int] = [31]*6
        self._effort: list[int] = [0]*6
        self._stats: list[int] = [100]*6
        self._terastal: str = ""
        self.is_terastallized: bool = False

        self.observed: bool
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

    def enter(self, battle: Battle):
        self.observed = True
        self.ability.register_handlers(battle)
        self.item.register_handlers(battle)
        battle.add_turn_log(battle.idx(self), f"{self.name} 着地")

    def try_use_move(self, battle: Battle, move: Move, target: Pokemon):
        battle.run_move(move, user=self, target=target)

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
                    v = int((self.data.base[0]*2+self._indiv[0]+int(eff/4))*self._level/100)+self._level+10
                else:
                    v = int((int((self.data.base[i]*2+self._indiv[i]+int(eff/4))*self._level/100)+5)*nc[i])
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

        self._stats[0] = int((self.base[0]*2+self._indiv[0] + int(self._effort[0]/4)) * self._level/100) + self._level + 10

        for i in range(1, 6):
            self._stats[i] = int((int((self.base[i]*2 + self._indiv[i] + int(self._effort[i]/4)) * self._level/100) + 5) *
                                 NATURE_MODIFIER[self._nature][i])

        if keep_damage:
            self.hp = self.hp - damage

    def set_stats(self, idx: int, value: int) -> bool:
        nc = NATURE_MODIFIER[self._nature]
        efforts_50 = [0] + [4+8*i for i in range(32)]

        for eff in efforts_50:
            if idx == 0:
                v = int((self.data.base[0]*2+self._indiv[0]+int(eff/4))*self._level/100)+self._level+10
            else:
                v = int((int((self.data.base[idx]*2+self._indiv[idx]+int(eff/4))*self._level/100)+5)*nc[idx])
            if v == value:
                self._effort[idx] = eff
                self._stats[idx] = v
                return True

        return False

    def set_effort(self, idx: int, value: int):
        self._effort[idx] = value
        self.update_stats()

    def modify_hp(self, battle: Battle, v: int):
        old = self.hp
        self.hp = max(0, min(self.max_hp, self.hp + v))
        diff = self.hp - old
        if diff:
            battle.add_turn_log(battle.idx(self), f"HP {'+' if diff >= 0 else ''}{diff}")

    def terastallize(self) -> bool:
        if self.is_terastallized:
            return False
        self.is_terastallized = True
        return True

    def find_move(self, move: Move | str) -> Move | None:
        for mv in self.moves:
            if move in [mv, mv.name]:
                return mv

    def knows(self, move: Move | str) -> bool:
        return self.find_move(move) is not None

    def is_sleeping(self) -> bool:
        return self.ailment == Ailment.SLP or self.ability.name == "ぜったいねむり"
