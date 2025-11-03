from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..battle import Battle

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Phase
from pokebot.common.types import PlayerIndex


def _mask(self: Battle,
          perspective: PlayerIndex | int):

    opp_idx = not perspective
    opponent = self.players[opp_idx]

    # 方策関数の隠蔽
    opponent.selection_commands = opponent._random_select
    opponent.action_command = opponent._random_command
    opponent.switch_command = opponent._random_command

    # パーティの隠蔽
    for p in opponent.team:
        p.mask()

    # 選出の隠蔽
    self.selection_indexes[opp_idx] = [i for i in self.selection_indexes[opp_idx] if opponent.team[i].observed]

    # 相手の選出を補完
    self.players[perspective].complement_opponent_selection(self)

    if not self.pokemons[opp_idx]:
        return

    # 相手が後手かつ未行動なら、相手が選択した技を補完
    if opp_idx != self.turn_mgr.first_player_idx and \
            self.turn_mgr._second_player_has_act and \
            self.poke_mgrs[opp_idx].forced_turn == 0:
        self.turn_mgr.move[opp_idx] = self.players[perspective].complement_opponent_move(self)

    # このターンに場の相手ポケモンが瀕死なら、相手の交代コマンドを補完
    if self.phase == Phase.SWITCH and self.pokemons[opp_idx].hp == 0:
        self.turn_mgr.scheduled_switch_commands[opp_idx].append(
            self.players[perspective].complement_opponent_switch(self))
