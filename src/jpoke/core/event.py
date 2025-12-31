from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from jpoke.core.battle import Battle
    from jpoke.model.pokemon import Pokemon
    from jpoke.model.move import Move

from typing import Callable
from dataclasses import dataclass
from enum import Enum, auto

from jpoke.utils import copy_utils as copyut
from jpoke.player import Player


class Event(Enum):
    ON_BEFORE_ACTION = auto()
    ON_SWITCH_IN = auto()
    ON_SWITCH_OUT = auto()
    ON_BEFORE_MOVE = auto()
    ON_TRY_ACTION = auto()
    ON_TRY_MOVE = auto()
    ON_TRY_IMMUNE = auto()
    ON_HIT = auto()
    ON_PAY_HP = auto()
    ON_MODIFY_DAMAGE = auto()
    ON_MOVE_SECONDARY = auto()
    ON_DAMAGE = auto()
    ON_AFTER_PIVOT = auto()
    ON_TURN_END_1 = auto()
    ON_TURN_END_2 = auto()
    ON_TURN_END_3 = auto()
    ON_TURN_END_4 = auto()
    ON_TURN_END_5 = auto()
    ON_TURN_END_6 = auto()
    ON_MODIFY_STAT = auto()
    ON_END = auto()
    ON_CHECK_TRAP = auto()
    ON_CHECK_NERVOUS = auto()
    ON_CHECK_MOVE_TYPE = auto()
    ON_CHECK_MOVE_CATEGORY = auto()

    ON_CALC_SPEED = auto()
    ON_CALC_ACTION_SPEED = auto()
    ON_CALC_ACCURACY = auto()
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
    EMERGENCY = auto()
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


@dataclass
class EventContext:
    source: Pokemon
    move: Move = None  # type: ignore
    by_foe: bool = False


@dataclass(frozen=True)
class Handler:
    func: Callable
    priority: int = 0
    once: bool = False

    def __lt__(self, other):
        return self.priority > other.priority


class HandlerResult(Enum):
    NONE = None
    STOP_HANDLER = auto()
    STOP_EVENT = auto()


class EventManager:
    def __init__(self, battle: Battle) -> None:
        self.battle = battle
        self.handlers: dict[Event, dict[Handler, list[Pokemon | Player]]] = {}

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        return copyut.fast_copy(self, new)

    def update_reference(self, new: Battle):
        old = self.battle

        # ハンドラの対象に指定されているポケモンまたはプレイヤーへの参照を更新する
        for event, data in self.handlers.items():
            for handler, sources in data.items():
                new_sources = []
                for old_source in sources:
                    # プレイヤーまたはポケモンのインデックスから複製後のオブジェクトを見つける
                    if isinstance(old_source, Player):
                        player_idx = old.players.index(old_source)
                        new_source = new.players[player_idx]
                    else:
                        old_player = old.find_player(old_source)
                        player_idx = old.players.index(old_player)
                        team_idx = old_player.team.index(old_source)
                        new_source = new.players[player_idx].team[team_idx]
                    new_sources.append(new_source)

                self.handlers[event][handler] = new_sources

        # Battle への参照を更新する
        self.battle = new

    def on(self, event: Event, handler: Handler, source: Pokemon | Player):
        """イベントを指定してハンドラを登録"""
        self.handlers.setdefault(event, {})
        sources = self.handlers[event].setdefault(handler, [])
        if source not in sources:
            sources.append(source)

    def off(self, event: Event, handler: Handler, source: Pokemon | Player):
        if event in self.handlers and handler in self.handlers[event]:
            # source を削除
            self.handlers[event][handler] = \
                [p for p in self.handlers[event][handler] if p != source]
            # 空のハンドラを解除
            if not self.handlers[event][handler]:
                del self.handlers[event][handler]

    def emit(self, event: Event, ctx: EventContext | None = None, value: Any = None) -> Any:
        """イベントを発火"""
        for handler, sources in sorted(self.handlers.get(event, {}).items()):
            # 引数のコンテキストを優先し、指定がなければ登録されているsourceを参照する
            if ctx:
                ctxs = [ctx]
            else:
                # sources: list[Pokemon | Player] の全要素を場のポケモンに置き換える
                new_sources = []
                for source in sources:
                    if isinstance(source, Player):
                        source = self.battle.active(source)
                    if source not in new_sources:
                        new_sources.append(source)

                # 素早さ順に並び変える
                if len(new_sources) > 1:
                    order = self.battle.get_speed_order()
                    new_sources = [p for p in order if p in new_sources]

                ctxs = [EventContext(source) for source in new_sources]

            # すべての source に対してハンドラを実行する
            for c in ctxs:
                res = handler.func(self.battle, c, value)

                # 単発ハンドラの削除
                if handler.once:
                    self.off(event, handler, c.source)

                if isinstance(res, HandlerResult):
                    flag = res
                elif isinstance(res, tuple):
                    value, flag = res
                else:
                    value, flag = res, None

                match flag:
                    case HandlerResult.STOP_HANDLER:
                        break
                    case HandlerResult.STOP_EVENT:
                        return value

        return value
