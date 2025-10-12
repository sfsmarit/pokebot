from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..battle import Battle

from pokebot.common.enums import Breakpoint
from pokebot.core.events import Event


def advance_turn(self: Battle):
    if not any(self.breakpoint):
        self.init_turn()

    if self.turn == 0:
        # ポケモンを選出
        self.run_selection()

        # ポケモンを場に出す
        self.run_initial_switch()

        # だっしゅつパックによる交代
        for idx in self.get_speed_order():
            if self.breakpoint[idx] == Breakpoint.REQUESTED:
                self.breakpoint[idx] = Breakpoint.EJECTPACK_ON_START
                self.run_switch(idx, self.query_switch(idx))
                break

        return

    # 行動選択
    for idx, player in enumerate(self.player):
        self.command[idx] = player.get_action_command(self)

    # 交代前の処理
    self.events.emit(Event.ON_BEFORE_ACTION)

    # 交代
    for idx in self.get_action_order():
        if self.command[idx].is_switch():
            self.run_switch(idx, self.player[idx].team[self.command[idx].idx])
        else:
            self.add_turn_log(idx, self.actives[idx].name)

    for idx in self.get_action_order():
        # このターンに交代済みなら行動不可
        if self.already_switched[idx]:
            continue

        # 技の発動
        move = self.get_move_from_command(idx, self.command[idx])
        self.run_move(idx, move)

        # だっしゅつボタンによる交代
        if self.breakpoint[not idx] == Breakpoint.EJECTBUTTON:
            self.run_switch(not idx, self.query_switch(not idx))

        # 交代技による交代
        if self.breakpoint[idx] == Breakpoint.PIVOT:
            self.run_switch(idx, self.query_switch(idx))

    # ターン終了
    self.events.emit(Event.ON_TURN_END)

    # だっしゅつパックによる交代
    for idx in self.get_speed_order():
        if self.breakpoint[idx] == Breakpoint.REQUESTED:
            self.breakpoint[idx] = Breakpoint.EJECTPACK_ON_TURNEND
            self.run_switch(idx, self.query_switch(idx))
            break

    # 瀕死による交代
    self.run_faint_switch()
