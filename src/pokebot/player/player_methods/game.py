from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..player import Player

from pokebot.core.battle import Battle


def _game(self: Player,
          opponent: Player,
          n_selection: int,
          open_sheet: bool,
          seed: int,
          max_turn: int,
          display_log: bool,
          is_test: bool) -> Battle:

    battle = Battle(player1=self,
                    player2=opponent,
                    n_selection=n_selection,
                    open_sheet=open_sheet,
                    seed=seed,
                    is_test=is_test)

    # 選出
    battle.select_pokemon()

    # 勝敗が決まるまでターンを進める
    while battle.winner(TOD=battle.turn >= max_turn) is None:
        self.advance_turn(battle, display_log)

    # 戦績の更新
    self.n_game += 1
    opponent.n_game += 1

    if battle.winner() == 0:
        self.n_won += 1
    else:
        opponent.n_won += 1

    self.update_rating(opponent, won=(battle.winner() == 0))

    return battle
