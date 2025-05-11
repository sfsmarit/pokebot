from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.battle.battle import Battle

from pokebot.common.types import PlayerIndex
from pokebot.logger import TurnLog
from pokebot.logger.command_log import CommandLog


def _winner(self: Battle,
            TOD: bool = False) -> PlayerIndex | None:
    """
    勝敗を判定する

    Parameters
    ----------
    TOD : bool, optional
        TrueならTOD判定を行う, by default False

    Returns
    -------
    bool
        勝利したプレイヤー番号
    """

    if self._winner is not None:
        return self._winner

    TOD_scores = [TOD_score(self, PlayerIndex(i)) for i in range(2)]

    if 0 in TOD_scores or TOD:
        self._winner = PlayerIndex(TOD_scores.index(max(TOD_scores)))
        self.logger.append(TurnLog(self.turn, self._winner, "勝ち"))
        self.logger.append(TurnLog(self.turn, not self._winner, "負け"))
        self.logger.append(CommandLog(self.turn, self.turn_mgr.command, self.turn_mgr.switch_command_history))

    return self._winner


def TOD_score(self: Battle,
              idx: PlayerIndex,
              alpha: float = 1) -> float:
    """
    TODスコア = (残数) + alpha * (残りHP割合)
    """
    n_alive, full_hp, total_hp = 0, 0, 0

    for p in self.selected_pokemons(idx):
        full_hp += p.stats[0]
        total_hp += p.hp
        if p.hp:
            n_alive += 1

    return n_alive + alpha * total_hp / full_hp
