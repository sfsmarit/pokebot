from jpoke.utils.types import Stat, BoostSource, get_stats
from jpoke.utils import copy_utils as copyut
from .move import Move


class FieldStatus:
    def __init__(self) -> None:
        self.choice_locked: bool = False
        self.hidden: bool = False
        self.lockon: bool = False
        self.active_turn: int = 0
        self.forced_turn: int = 0
        self.sub_hp: int = 0
        self.bind_damage_denom: int = 0
        self.hits_taken: int = 0
        self.boosted_stat: Stat | None = None
        self.boost_source: BoostSource = ""
        self.rank: dict[Stat, int] = {k: 0 for k in get_stats()}  # type: ignore
        self.added_types: list[str] = []
        self.lost_types: list[str] = []
        self.executed_move: Move | None = None
        self.expended_moves: list[Move] = []

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        copyut.fast_copy(self, new, keys_to_deepcopy=['executed_move', 'expended_moves'])
        return new
