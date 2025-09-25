from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from copy import deepcopy

from pokebot.common.types import PlayerIndex
import pokebot.common.utils as ut
from pokebot.pokedb import Move


class DamageLog:
    def __init__(self,
                 battle: Battle,
                 atk: PlayerIndex | int,
                 move: Move):

        self.turn: int = battle.turn
        self.idx: PlayerIndex | int = atk
        self.pokemons: list[dict] = [p.dump() for p in battle.pokemons]
        self.poke_mgrs: list[dict] = [mgr.dump() for mgr in battle.poke_mgrs]
        self.move: str = move.name
        self.damage_dealt: int = battle.turn_mgr.damage_dealt[atk]
        self.damage_ratio: float = self.damage_dealt / battle.pokemons[not atk].stats[0]
        self.critical: bool = battle.damage_mgr.critical
        self.field_mgr: dict = battle.field_mgr.dump()

        self.notes: list[str] = []
        self.item_consumed: list[bool] = [False, False]

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new)
        return new

    def mask(self):
        pass

    def masked(self):
        masked = deepcopy(self)
        masked.mask()
        return masked

    def is_estimable(self) -> bool:
        return True
