from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..player import Player

from pokebot.common.enums import Command
from pokebot.core import Battle
from pokebot.core.move_utils import move_speed


def _max_damage_command(self: Player, battle: Battle) -> Command:
    """ターン行動の方策関数"""
    available_commands = battle.available_commands(self.idx)

    if len(available_commands) == 1:
        # 選択肢がない (わるあがきも含まれる)
        return available_commands[0]

    if battle.pokemons[not self.idx].hp == 0:
        # 実機対戦のバグ(?)対策
        return available_commands[0]

    # 相手の情報を推定する
    self.estimate_opponent_stats(battle)  # 相手のステータス推定

    # 技のダメージからスコアを計算する
    n = len(available_commands)
    scores = [0.]*n

    for i, command in enumerate(available_commands):
        # 交代しない
        if command.is_switch:
            continue

        move = battle.pokemons[self.idx].moves[command.index]

        # テラスタル判定
        battle.pokemons[self.idx].is_terastallized = command.is_terastal

        # リーサル計算
        battle.damage_mgr.lethal(self.idx, [move])

        # ダメージ
        damages = list(map(int, battle.damage_mgr.damage_dstr.keys()))

        # コマンドごとのスコアを計算
        if damages[0]:
            min_damage_ratio = min(1, damages[0] / battle.pokemons[not self.idx].hp)
            speed = move_speed(battle, self.idx, move)
            scores[i] = (min_damage_ratio + speed*1e-2)  # * move.hit/100
            print("スコア\n"*(i == 0) + f"\t{battle.command_to_str(self.idx, command)} {scores[i]:.3f}")

    # 最大スコアを選択
    return available_commands[scores.index(max(scores))]
