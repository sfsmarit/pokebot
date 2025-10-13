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
    ON_BEFORE_ACTION = auto()
    ON_SWITCH_IN = auto()
    ON_SWITCH_OUT = auto()
    ON_BEFORE_MOVE = auto()
    ON_TRY_MOVE = auto()
    ON_HIT = auto()
    ON_DAMAGE = auto()
    ON_TURN_END = auto()
    ON_MODIFY_STAT = auto()
    ON_END = auto()
    ON_CHECK_TRAP = auto()
    ON_CHECK_MOVE_TYPE = auto()
    ON_CHECK_MOVE_CATEGORY = auto()

    ON_CALC_POWER_MODIFIER = auto()
    ON_CALC_ATK_MODIFIER = auto()
    ON_CALC_DEF_MODIFIER = auto()
    ON_CALC_ATK_TYPE_MODIFIER = auto()
    ON_CALC_DEF_TYPE_MODIFIER = auto()
    ON_CALC_DAMAGE_MODIFIER = auto()
    ON_CHECK_DEF_ABILITY = auto()


@dataclass
class Handler:
    func: Callable
    priority: int = 0
    once: bool = False

    def __lt__(self, other: Handler):
        return self.priority > other.priority


@dataclass
class EventContext:
    source: Pokemon = None  # type: ignore
    move: Move = None  # type: ignore
    value: Any = 0
    by_foe: bool = False


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

    def emit(self, event: Event, ctx: EventContext | None = None) -> Any:
        """イベントを発火"""
        for h in sorted(self.handlers.get(event, [])):
            if ctx is None:
                ctxs = [EventContext(self.battle.actives[i])
                        for i in self.battle.get_action_order()]
            else:
                ctxs = [ctx]

            for c in ctxs:
                result = h.func(self.battle, c)

                # 単発ハンドラを削除
                if h.once:
                    self.off(event, h)

                # 処理を中断
                if result == False:
                    return c.value

        return ctx.value if ctx else 0
