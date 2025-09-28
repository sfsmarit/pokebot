from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle
    from pokebot.core.pokemon import Pokemon

from pokebot.common.enums import Stat, BoostSource
from .move import Move


class ActiveStatus:
    def __init__(self, owner: Pokemon) -> None:
        self.choice_locked: bool = False
        self.nervous: bool = False
        self.hidden: bool = False
        self.lockon: bool = False
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
