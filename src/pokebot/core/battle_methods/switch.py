from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..battle import Battle

from pokebot.common.enums import Breakpoint
from pokebot.core.events import Event, EventContext
from pokebot.core.pokemon import Pokemon


def run_switch(self: Battle,
               player_idx: int,
               new: Pokemon,
               emit_switch_in: bool):
    # 退場
    old = self.actives[player_idx]
    if old is not None:
        self.events.emit(Event.ON_SWITCH_OUT, EventContext(self.actives[player_idx]))
        old.switch_out(self.events)
        self.add_turn_log(old, f"{old} {'退場' if old.hp else '瀕死'}")

    # 入場
    self.actives[player_idx] = new
    new.switch_in(self.events)
    self.add_turn_log(new, f"{new} 入場")
    if emit_switch_in:
        self.events.emit(Event.ON_SWITCH_IN, EventContext(self.actives[player_idx]))

    # Breakpoint 破棄
    self.breakpoint[player_idx] = None

    self.already_switched[player_idx] = True


def run_initial_switch(self: Battle):
    # ポケモンを場に出す
    # 場に出たときの処理は両者の交代が完了したあとに行う
    for idx, player in enumerate(self.player):
        new = player.team[self.selection_idxes[idx][0]]
        self.run_switch(idx, new, emit_switch_in=False)

    # ポケモンが場に出たときの処理
    self.events.emit(Event.ON_SWITCH_IN)


def run_faint_switch(self: Battle):
    while self.winner() is None:
        # Breakpoint を設定
        if not any(self.breakpoint):
            for i, poke in enumerate(self.actives):
                if poke.hp == 0:
                    self.breakpoint[i] = Breakpoint.FAINTED

        # 交代を行うプレイヤー
        idxes = [i for i in range(2) if self.breakpoint[i] == Breakpoint.FAINTED]

        # 対象プレイヤーがいなければ終了
        if not idxes:
            return

        # ポケモンを場に出す
        # 場に出たときの処理は両者の交代が完了したあとに行う
        for idx in idxes:
            new = self.query_switch(idx)
            self.run_switch(idx, new, emit_switch_in=False)

        # ポケモンが場に出たときの処理
        self.events.emit(Event.ON_SWITCH_IN)
