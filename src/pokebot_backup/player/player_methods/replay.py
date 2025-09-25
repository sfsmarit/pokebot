from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..player import Player

import json

from pokebot.common.enums import Command
from pokebot.pokedb import Pokemon
from pokebot.core.battle import Battle


def find_command_log(log: dict, turn: int) -> dict:
    for d in log["command_logs"]:
        if d["turn"] == turn:
            return d
    return {}


def _replay(cls: type[Player], filepath: str, display_log: bool = True) -> Battle:

    with open(filepath, encoding='utf-8') as fin:
        log = json.load(fin)

        n_selection = len(log["selection_indexes"][0])
        seed = log['seed']

        # パーティの再現
        players = []
        for idx in range(2):
            player = cls()

            for i, d in enumerate(log[f"teams"][idx]):
                p = Pokemon()
                p.load(d)
                if display_log:
                    print(f"Player_{idx} #{i} {p}\n")
                player.team.append(p)

            players.append(player)

        if display_log:
            print('-'*50)

        # Battleを生成
        battle = Battle(players[0], players[1], n_selection=n_selection, seed=seed)
        battle.init_game()

        # 選出
        battle.selection_indexes = log[f"selection_indexes"]

        while True:
            # コマンドを取得
            command_log = find_command_log(log, battle.turn + 1)

            if not command_log:
                return battle

            # 予定されている交代を設定
            battle.turn_mgr.scheduled_switch_commands = \
                [[Command(v) for v in commands] for commands in command_log['switch_commands']]

            # コマンドにしたがってターンを進める
            commands = [Command(v) for v in command_log['command']]
            battle.advance_turn(commands=commands)

            # ログ表示
            if display_log:
                print(f"ターン{battle.turn}")
                for idx in battle.action_order:
                    print(f"\tPlayer {int(idx)}",
                          ", ".join(battle.logger.get_turn_log(battle.turn, idx)))
