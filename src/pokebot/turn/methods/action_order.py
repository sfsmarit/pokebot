from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import GlobalField, Command
from pokebot.core import Move
from pokebot.logger import TurnLog
from pokebot.move import move_speed


def _update_action_order(self: TurnManager):
    """場のポケモンの行動順を更新する"""
    battle = self.battle

    # 素早さ順の更新
    update_speed_order(self)

    action_speeds = [0., 0.]

    for idx in range(2):
        idx = PlayerIndex(idx)
        poke = battle.pokemon[idx]
        poke_mgr = battle.poke_mgr[idx]

        # 素早さ順 (1e-2)
        action_speeds[idx] -= self.speed_order.index(idx) * 1e-2

        # 行動スキップ (1e+3)
        if self.command[idx] == Command.SKIP:
            action_speeds[idx] += 1e3
            continue

        # 交代 (1e+1)
        if self.command[idx].is_switch:
            action_speeds[idx] += 1e1
            continue

        if self.command[idx].is_battle:
            # 技選択
            self.move[idx] = poke.moves[self.command[idx].index]
        elif self.command[idx] == Command.STRUGGLE:
            # わるあがき
            self.move[idx] = Move('わるあがき')
        elif self.command[idx] == Command.FORCED:
            # 強制行動
            if "immovable" in poke_mgr.executed_move.tags:
                # 反動
                self.move[idx] = Move()
                battle.poke_mgr[idx].unresponsive_turn = 0
            else:
                # 前ターンと同じ技
                self.move[idx] = poke_mgr.executed_move

        if not self.move[idx]:
            continue

        # 技の優先度 (1e-1~1e0)
        self.move_speed[idx] = move_speed(battle, idx, self.move[idx])
        action_speeds[idx] += self.move_speed[idx]

    # 行動順を更新
    battle.turn_mgr.first_player_idx = PlayerIndex(action_speeds[0] < action_speeds[1])


def update_speed_order(self: TurnManager):
    """場のポケモンの素早さ順を更新する"""
    battle = self.battle

    if not all(battle.pokemon):
        return

    # 場のポケモンの素早さを取得
    speeds = []
    for idx in range(2):
        speeds.append(battle.poke_mgr[idx].effective_speed())
        if battle.field_mgr.count[GlobalField.TRICKROOM]:
            speeds[idx] = 1 / speeds[idx]

    # 同速判定
    if speeds[0] == speeds[1]:
        idx = battle.random.randint(0, 1)
        speeds[idx] += 1
        battle.logger.append(TurnLog(battle.turn, idx, '同速+1'))

    # 素早さ順を更新
    first = speeds.index(max(speeds))
    self.speed_order = [PlayerIndex(first), PlayerIndex(not first)]


def _estimate_opponent_speed(self: TurnManager, idx: PlayerIndex):
    """行動順から相手のポケモンの素早さを推定する"""
    battle = self.battle

    opp = PlayerIndex(not idx)
    opponent = battle.pokemon[opp]
    masked_opp = opponent if battle.open_sheet else opponent.masked()

    # 観測可能な相手のS補正値
    r_speed = battle.masked(idx).poke_mgr[opp].effective_speed() / masked_opp.stats[5]

    # 相手のS = 自分のS / 相手のS補正値
    speed = int(battle.poke_mgr[idx].effective_speed() / r_speed)

    # S推定値を更新
    opponent.set_speed_limit(speed, first_act=battle.poke_mgr[opp].first_act)
