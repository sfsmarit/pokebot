from pokebot.sv.pokeDB import PokeDB
from pokebot.sv.battle import Battle, CommandRange
from pokebot.sv.player import Player


class MaxDamagePlayer(Player):
    """最大威力・先制・(命中安定)の技を選ぶ"""

    def __init__(self):
        super().__init__()

    def battle_command(self, battle: Battle) -> int:
        """ターン行動の方策関数"""
        pidx = self.idx
        available_commands = battle.available_commands(pidx)

        # 相手のHPが0の場合
        if not battle.pokemon[not pidx].hp:
            return available_commands[0]

        # 相手の情報を推定する
        self.update_rejected_items(battle)  # 相手のアイテム候補の棄却
        self.update_opponent_stats(battle)  # 相手のステータス推定

        # 選択可能な技について、推定されるダメージからスコアを計算する
        n = len(available_commands)
        scores = [0]*n

        for i, cmd in enumerate(available_commands):
            # 交代しない
            if cmd not in CommandRange['move']:
                break

            move = battle.pokemon[pidx].moves[cmd % 10]

            # テラスタル発動
            if cmd in CommandRange['terastal']:
                battle.pokemon[pidx].terastallize()

            # 確定急所の判定
            critical = move.name in PokeDB.move_category['critical']

            # リーサル計算
            text = battle.lethal(pidx, [move], critical=critical)
            # print("ダメージ計算\n"*(i==0) + f"\t{battle.cmd2str(pidx, cmd)} {text}")

            # ダメージ
            damages = list(map(int, battle.damage_dict.keys()))

            # コマンドごとのスコアを計算
            if damages[0]:
                min_damage_ratio = min(1, damages[0] / battle.pokemon[not pidx].hp)
                move_speed = battle.move_speed(pidx, move)
                scores[i] = (min_damage_ratio + move_speed*1e-3)  # * move.hit/100
                print("スコア\n"*(i == 0) + f"\t{battle.cmd2str(pidx, cmd)} {scores[i]:.3f}")

        # 最大スコアを選択
        return available_commands[scores.index(max(scores))]


class MCTSPlayer(Player):
    """MCTSに基づいて勝率が最大となる行動をとる"""

    def __init__(self, n_search: int = 1000):
        super().__init__()


class UCTSPlayer(Player):
    """UCTSに基づいて勝率が最大となる行動をとる"""

    def __init__(self, n_search: int = 1000):
        super().__init__()


class NashPlayer(Player):
    """ナッシュ均衡戦略に従う"""

    def __init__(self, n_search: int = 1000):
        super().__init__()
