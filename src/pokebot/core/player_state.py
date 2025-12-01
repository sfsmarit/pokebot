from pokebot.utils import copy_utils as copyut
from pokebot.utils.enums import Command

from .events import Interrupt


class PlayerState:
    def __init__(self) -> None:
        self.selected_idxes: list[int] = []
        self.active_idx: int = None  # type: ignore
        self.interrupt: Interrupt = Interrupt.NONE
        self.reserved_commands: list[Command] = []

        self.reset_turn()

    def reset_turn(self):
        self.already_switched = False

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return copyut.fast_copy(self, new)
