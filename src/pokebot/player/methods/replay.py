from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..random_player import RandomPlayer

import json

from pokebot.common.enums import Mode, Command
from pokebot.core import Pokemon
from pokebot.battle.battle import Battle


def find_command_log(log: dict, turn: int) -> dict:
    for d in log["command_logs"]:
        if d["turn"] == turn:
            return d
    return {}


def _replay(cls: type[RandomPlayer],
            filepath: str,
            mute: bool = False) -> Battle:

    with open(filepath, encoding='utf-8') as fin:
        log = json.load(fin)

        mode = Mode(log['mode'])
        n_selection = len(log["selection_indexes"][0])
        seed = log['seed']

        # パーティの再現
        players = []
        for idx in range(2):
            player = cls()

            for i, d in enumerate(log[f"teams"][idx]):
                p = Pokemon()
                p.load(d)
                if not mute:
                    print(f"Player_{idx} #{i} {p}\n")
                player.team.append(p)

            players.append(player)

        if not mute:
            print('-'*50)

        # Battleを生成
        battle = Battle(players[0], players[1], mode=mode, n_selection=n_selection, seed=seed)
        battle.init_game()

        # 選出
        battle.selection_indexes = log[f"selection_indexes"]

        while True:
            # コマンドを取得
            command_log = find_command_log(log, battle.turn + 1)

            if not command_log:
                return battle

            # 交代コマンドを予約
            battle.turn_mgr.scheduled_switch_commands = \
                [[Command(v) for v in commands] for commands in command_log['switch_commands']]

            # コマンドにしたがってターンを進める
            commands = [Command(v) for v in command_log['command']]
            battle.advance_turn(commands=commands)

            # ログ表示
            if not mute:
                print(f"ターン{battle.turn}")
                for idx in battle.action_order:
                    print(f"\tPlayer {int(idx)}", battle.logger.summary(battle.turn, idx))
