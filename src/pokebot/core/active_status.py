from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle
    from pokebot.core.pokemon import Pokemon

from pokebot.common.enums import Event, Stat, BoostSource

from .move import Move


class ActiveStatus:
    def __init__(self, owner: Pokemon) -> None:
        self.owner: Pokemon = owner

        self.choice_locked: bool = False
        self.hidden: bool = False
        self.lockon: bool = False
        self.rank_dropped: bool = False
        self.berserk_triggered: bool = False
        self.active_turn: int = 0
        self.forced_turn: int = 0
        self.sub_hp: int = 0
        self.bind_damage_denom: int = 0
        self.hits_taken: int = 0
        self.boosted_stat: Stat | None = None
        self.boost_source: BoostSource = BoostSource.NONE
        self.rank: list[int] = [0] * len(Stat)
        self.added_types: list[str] = []
        self.lost_types: list[str] = []
        self.executed_move: Move | None = None
        self.expended_moves: list[Move] = []
        self.count: dict = {}

    def modify_rank(self, battle: Battle, stat: Stat, v: int) -> bool:
        old = self.rank[stat.idx]
        self.rank[stat.idx] = max(-6, min(6, old + v))
        diff = self.rank[stat.idx] - old

        if diff:
            battle.add_turn_log(self.owner, f"{stat.name}{'+' if diff >= 0 else ''}{diff}")

        if diff > 0:
            battle.events.emit(Event.ON_RANK_UP, battle, self.owner)
        elif diff < 0:
            battle.events.emit(Event.ON_RANK_DOWN, battle, self.owner)

        return diff != 0
