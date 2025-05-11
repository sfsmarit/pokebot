from pokebot.common.enums import Command
from pokebot.battle.battle import Battle
from pokebot.player.random_player import RandomPlayer


class MaxDamagePlayer(RandomPlayer):
    """最大威力・先制・(命中安定)の技を選ぶ"""

    def __init__(self):
        super().__init__()

    def battle_command(self, battle: Battle) -> int | Command:
        """ターン行動の方策関数"""
        available_commands = battle.available_commands(self.idx)

        # 相手のHPが0の場合
        if not battle.pokemon[not self.idx].hp:
            return available_commands[0]

        # 相手の情報を推定する
        self.update_rejected_items(battle)  # 相手のアイテム候補の棄却
        self.estimate_opponent_stats(battle)  # 相手のステータス推定

        # 選択可能な技について、推定されるダメージからスコアを計算する
        n = len(available_commands)
        scores = [0.]*n

        for i, cmd in enumerate(available_commands):
            # 技以外のコマンドを除外
            if cmd.value[0] not in ["MOVE", "TERASTAL"]:
                continue

            move = battle.pokemon[self.idx].moves[cmd.index]

            # テラスタル発動
            if cmd.value[0] == "TERASTAL":
                battle.pokemon[self.idx].terastallize()

            # リーサル計算
            text = battle.damage_mgr.lethal(self.idx, [move])
            # print("ダメージ計算\n"*(i==0) + f"\t{battle.cmd2str(pidx, cmd)} {text}")

            # ダメージ
            damages = list(map(int, battle.damage_mgr.damage_dstr.keys()))

            # コマンドごとのスコアを計算
            if damages[0]:
                min_damage_ratio = min(1, damages[0] / battle.pokemon[not self.idx].hp)
                move_speed = battle.move_mgr.move_speed(self.idx, move)
                scores[i] = (min_damage_ratio + move_speed*1e-3)  # * move.hit/100
                print("スコア\n"*(i == 0) + f"\t{battle.command_to_str(self.idx, cmd)} {scores[i]:.3f}")

        # 最大スコアを選択
        return available_commands[scores.index(max(scores))]


class MCTSPlayer(RandomPlayer):
    """MCTSに基づいて勝率が最大となる行動をとる"""

    def __init__(self, n_search: int = 1000):
        super().__init__()


class UCTSPlayer(RandomPlayer):
    """UCTSに基づいて勝率が最大となる行動をとる"""

    def __init__(self, n_search: int = 1000):
        super().__init__()


class NashPlayer(RandomPlayer):
    """ナッシュ均衡戦略に従う"""

    def __init__(self, n_search: int = 1000):
        super().__init__()
