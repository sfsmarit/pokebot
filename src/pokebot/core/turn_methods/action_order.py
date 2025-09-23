from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import GlobalField, Command
from pokebot.model import Move
from pokebot.logger import TurnLog
from pokebot.core.move_utils import move_speed


def _update_action_order(self: TurnManager):
    """場のポケモンの行動順を更新する"""
    # 素早さ順の更新
    update_speed_order(self)

    action_speeds = [0., 0.]

    for idx in range(2):
        poke = self.battle.pokemons[idx]
        poke_mgr = self.battle.poke_mgrs[idx]

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

        if self.command[idx].is_action:
            # 技選択
            self.move[idx] = poke.moves[self.command[idx].index]
        elif self.command[idx] == Command.STRUGGLE:
            # わるあがき
            self.move[idx] = Move('わるあがき')
        elif self.command[idx] == Command.FORCED:
            # 強制行動
            if "immovable" in poke_mgr.executed_move.tags:
                # 反動で動けない技
                self.move[idx] = Move()
                self.battle.poke_mgrs[idx].forced_turn -= 1
            else:
                # 前ターンと同じ技
                self.move[idx] = poke_mgr.executed_move

        if not self.move[idx]:
            continue

        # 技の優先度 (1e-1~1e0)
        self.move_speed[idx] = move_speed(self.battle, idx, self.move[idx])
        action_speeds[idx] += self.move_speed[idx]

    # 行動順を更新
    self.battle.turn_mgr.first_player_idx = int(action_speeds[0] < action_speeds[1])


def update_speed_order(self: TurnManager):
    """場のポケモンの素早さ順を更新する"""
    battle = self.battle

    if not all(battle.pokemons):
        return

    # 場のポケモンの素早さを取得
    speeds = []
    for idx in range(2):
        speeds.append(battle.poke_mgrs[idx].effective_speed())
        if battle.field_mgr.count[GlobalField.TRICKROOM]:
            speeds[idx] = 1 / speeds[idx]

    # 同速判定
    if speeds[0] == speeds[1]:
        idx = battle.random.randint(0, 1)
        speeds[idx] += 1
        battle.logger.append(TurnLog(battle.turn, idx, '同速+1'))

    # 素早さ順を更新
    first = speeds.index(max(speeds))
    self.speed_order = [first, int(not first)]


def _update_opponent_speed_limit(self: TurnManager, idx: PlayerIndex | int) -> None:
    """行動順から相手のポケモンの素早さを推定する"""
    opp = PlayerIndex(not idx)
    opponent = self.battle.pokemons[opp]

    if self.battle.open_sheet:
        observed_effective_speed = self.battle.poke_mgrs[opp].effective_speed(masked=False)
        observed_stats = self.battle.pokemons[opp].stats
    else:
        observed_effective_speed = self.battle.poke_mgrs[opp].effective_speed(masked=True)
        observed_stats = self.battle.pokemons[opp].masked().stats

    # 相手ポケモンのS補正の観測値
    speed_modifier = observed_effective_speed / observed_stats[5]

    # 相手のSリミット = 自分のS / 相手のS補正値
    speed_limit = int(self.battle.poke_mgrs[idx].effective_speed() / speed_modifier)

    # S推定値を更新
    opponent.set_speed_limit(speed_limit, first_act=self.battle.poke_mgrs[opp].first_act)
