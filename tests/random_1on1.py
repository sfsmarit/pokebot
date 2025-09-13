import time
import random
from pokebot import PokeDB, Pokemon, Player


# random.seed(1)
max_turn = 3


M = 1  # 匹から
N = random.randint(1, M)  # 匹選ぶ


names = ["バシャーモ", "ラグラージ"]
abilities = ["", ""]
items = ["", ""]
moves = ["のしかかり", "のしかかり"]
efforts = [
    [0, 0, 0, 0, 0, 0],
    [252, 252, 252, 252, 252, 0],
]

# 2人のプレイヤーを生成
player = Player()
opponent = Player()

# ポケモンをM匹ずつパーティに追加
for i, pl in enumerate([player, opponent]):
    pl.team.append(Pokemon(names[i]))
    pl.team[-1].ability = abilities[i]
    pl.team[-1].item = items[i]
    pl.team[-1].moves.clear()
    pl.team[-1].add_move(moves[i])
    pl.team[-1].effort = efforts[i]


# 表示
for i, pl in enumerate([player, opponent]):
    for j, p in enumerate(pl.team):
        print(f"Player{i}   #{j} {p}\n")
print('-'*50)

# N匹を選出して対戦
t0 = time.time()
battle = player.game(opponent, n_selection=N, seed=0, max_turn=max_turn)
print(f"{time.time() - t0:.2f}s")
print('-'*50)

# リプレイ
if False:
    # ログ出力
    filepath = f"tests/random_battle.json"
    battle.write(filepath)
    # リプレイ再生
    print(f"\n{'-'*50}\nリプレイ {filepath}\n{'-'*50}")
    player.replay(filepath)
