from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..random_player import RandomPlayer

from pokebot.common.enums import Mode
from pokebot.battle.battle import Battle


def _game(self: RandomPlayer,
          opponent: RandomPlayer,
          mode: Mode,
          n_selection: int,
          open_sheet: bool,
          seed: int,
          max_turn: int,
          video_id: int,
          mute: bool) -> Battle:

    # レベルを50に修正
    if mode != Mode.OFFLINE:
        for p in self.team:
            p.level = 50

    if mode != Mode.SIM:
        # 実機対戦
        from pokebot.bot.real_battle import RealBattle
        battle = RealBattle(self, opponent, mode=mode, n_selection=n_selection,
                            open_sheet=open_sheet, seed=seed, video_id=video_id)
        battle.main_loop()

    else:
        # シミュレーション
        battle = Battle(self, opponent, mode=mode, n_selection=n_selection,
                        open_sheet=open_sheet, seed=seed)

        # 勝敗が決まるまでターンを進める
        while battle.winner(TOD=battle.turn >= max_turn) is None:
            self.advance_turn(battle, mute)

    # 戦績の更新
    self.n_game += 1
    opponent.n_game += 1

    if battle.winner() == 0:
        self.n_won += 1
    else:
        opponent.n_won += 1

    self.update_rating(opponent, won=(battle.winner() == 0))

    return battle
