from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle
    from .pokemon import Pokemon
    from .move import Move

from typing import Callable, Any
from dataclasses import dataclass
from enum import Enum, auto


class Event(Enum):
    ON_START = auto()
    ON_BEFORE_SWITCH = auto()
    ON_SWITCH_IN = auto()
    ON_BEFORE_MOVE = auto()
    ON_TRY_MOVE = auto()
    ON_HIT = auto()
    ON_DAMAGE = auto()
    ON_TURN_END = auto()
    ON_MODIFY_RANK = auto()
    ON_END = auto()


@dataclass
class Handler:
    func: Callable
    order: int
    once: bool = False

    def __lt__(self, other):
        return self.order < other.order


@dataclass
class EventContext:
    source: Pokemon = None  # type: ignore
    move: Move = None  # type: ignore
    value: Any = 0


class EventManager:
    def __init__(self, battle: Battle) -> None:
        self.battle = battle
        self.handlers = {}

    def on(self, event: Event, handler: Handler):
        """イベントにハンドラを登録"""
        self.handlers.setdefault(event, []).append(handler)

    def off(self, event: Event, handler: Handler):
        if event in self.handlers:
            self.handlers[event] = [
                h for h in self.handlers[event] if h != handler
            ]

    def emit(self, event: Event, ctx: EventContext | None = None):
        """イベントを発火"""
        if ctx is None:
            ctx = EventContext()

        for h in sorted(self.handlers.get(event, [])):
            for idx in self.battle.get_action_order():
                ctx.source = self.battle.actives[idx]
                result = h.func(self.battle, ctx)

                # 単発ハンドラを削除
                if h.once:
                    self.off(event, h)

                if result == False:
                    break

        return ctx.value
