from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.battle.battle import Battle

from copy import deepcopy

from pokebot.common.types import PlayerIndex
from pokebot.core import Pokemon
from pokebot.core import Move


class DamageLog:
    def __init__(self,
                 battle: Battle,
                 atk: PlayerIndex | int,
                 move: Move):
        self.turn: int = battle.turn
        self.atk: PlayerIndex = PlayerIndex(atk)
        self.pokemons: list[Pokemon] = battle.pokemon  # deepcopy(battle.pokemon)
        self.move_name: str = move.name
        self.damage_dealt: int = battle.turn_mgr.damage_dealt[atk]
        self.damage_ratio: float = battle.turn_mgr.damage_dealt[atk] / battle.pokemon[not atk].stats[0]
        self.critical: bool = battle.damage_mgr.critical
        self.stellar_boost: bool = move.type not in battle.poke_mgr[atk].consumed_stellar_types
        self.field_count: dict = battle.field_mgr.count.copy()

        self.notes: list[str] = []
        self.item_consumed: list[bool] = [False, False]

    def mask(self):
        pass

    def masked(self):
        masked = deepcopy(self)
        masked.mask()
        return masked

    def is_estimable(self) -> bool:
        return True
