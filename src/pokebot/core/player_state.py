from dataclasses import dataclass, field

from pokebot.common import utils as ut
from pokebot.common.enums import Command

from .events import Interrupt


@dataclass
class PlayerState:
    selected_idxes: list[int] = field(default_factory=list)
    active_idx: int = None  # type: ignore
    interrupt: Interrupt = Interrupt.NONE
    already_switched: bool = False
    reserved_commands: list[Command] = field(default_factory=list)

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return ut.fast_copy(self, new)

    def turn_reset(self):
        self.already_switched = False
