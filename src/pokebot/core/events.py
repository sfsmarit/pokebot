from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle
    from pokebot.core.pokemon import Pokemon
    from pokebot.core.move import Move

from typing import Callable, Any
from dataclasses import dataclass
from enum import Enum, auto

from pokebot.common import utils as ut


class Event(Enum):
    ON_BEFORE_ACTION = auto()
    ON_SWITCH_IN = auto()
    ON_SWITCH_OUT = auto()
    ON_BEFORE_MOVE = auto()
    ON_TRY_MOVE = auto()
    ON_HIT = auto()
    ON_DAMAGE = auto()
    ON_AFTER_PIVOT = auto()
    ON_TURN_END_1 = auto()
    ON_TURN_END_2 = auto()
    ON_TURN_END_3 = auto()
    ON_TURN_END_4 = auto()
    ON_TURN_END_5 = auto()
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


class Interrupt(Enum):
    NONE = auto()
    EJECTBUTTON = auto()
    PIVOT = auto()
    FAINTED = auto()
    REQUESTED = auto()
    EJECTPACK_ON_AFTER_SWITCH = auto()
    EJECTPACK_ON_START = auto()
    EJECTPACK_ON_SWITCH_0 = auto()
    EJECTPACK_ON_SWITCH_1 = auto()
    EJECTPACK_ON_AFTER_MOVE_0 = auto()
    EJECTPACK_ON_AFTER_MOVE_1 = auto()
    EJECTPACK_ON_TURN_END = auto()

    def consume_item(self) -> bool:
        return "EJECT" in self.name

    @classmethod
    def ejectpack_on_switch(cls, idx: int):
        return cls[f"EJECTPACK_ON_SWITCH_{idx}"]

    @classmethod
    def ejectpack_on_after_move(cls, idx: int):
        return cls[f"EJECTPACK_ON_AFTER_MOVE_{idx}"]


@dataclass(frozen=True)
class Handler:
    func: Callable
    priority: int = 0
    once: bool = False

    def __lt__(self, other: Handler):
        return self.priority > other.priority


@dataclass
class EventContext:
    source: Pokemon
    move: Move = None  # type: ignore
    by_foe: bool = False


class EventManager:
    def __init__(self, battle: Battle) -> None:
        self.battle = battle
        self.handlers: dict[Event, dict[Handler, list[Pokemon]]] = {}

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return ut.fast_copy(self, new)

    def on(self, event: Event, handler: Handler, source: Pokemon | None = None):
        """イベントを指定してハンドラを登録"""
        self.handlers.setdefault(event, {})
        sources = self.handlers[event].setdefault(handler, [])
        if all(x not in sources for x in [source, None]):
            self.handlers[event][handler].append(source)  # type: ignore

    def off(self, event: Event, handler: Handler, source: Pokemon | None = None):
        if event in self.handlers and handler in self.handlers[event]:
            # source を削除
            self.handlers[event][handler] = \
                [p for p in self.handlers[event][handler] if p != source]
            # source が不在ならハンドラを解除
            if not self.handlers[event][handler]:
                del self.handlers[event][handler]

    def emit(self,
             event: Event,
             value: Any = 0,
             ctx: EventContext | None = None) -> Any:
        """イベントを発火"""
        for handler, sources in sorted(self.handlers.get(event, {}).items()):
            if not sources:
                raise Exception(f"No source for handler {handler}")

            # sources を None を、すべての場のポケモンに置き換える
            if sources == [None]:
                sources = [self.battle.active(pl) for pl in self.battle.get_speed_order()]
                self.handlers[event][handler] = sources

            # コンテキストは引数を優先し、指定がなければ登録されているsourceを参照する
            if ctx:
                ctxs = [ctx]
            else:
                ctxs = [EventContext(poke) for poke in sources]  # type: ignore

            # すべての source に対してハンドラを実行する
            for c in ctxs:
                result = handler.func(self.battle, value, c)

                # 単発ハンドラなら削除
                if handler.once:
                    self.off(event, handler, c.source)

                # ハンドラの返り値が False なら処理を中断
                if result == False:
                    return value

                # ハンドラに渡す value を更新
                value = result

        return value
