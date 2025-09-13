"""
M匹のポケモンからN匹選んでランダム対戦
"""

import random
from pokebot import PokeDB, Pokemon, Player


M = 6  # 匹から
N = 3  # 匹選ぶ

# 2人のプレイヤーを生成
player = Player()
opponent = Player()

# M匹のパーティを生成
for i, pl in enumerate([player, opponent]):
    names = random.sample(list(PokeDB.zukan.keys()), M)
    for j, name in enumerate(names):
        pl.team.append(Pokemon(name))

# 表示
for i, pl in enumerate([player, opponent]):
    for j, poke in enumerate(pl.team):
        print(f"Player{i}   #{j} {poke}\n")
print('-'*50)

# N匹選出して対戦
battle = player.game(opponent, n_selection=N, seed=0)


# ログ出力・リプレイ再生
if False:
    print('-'*50)
    filepath = f"./random_battle.json"
    battle.write(filepath)
    player.replay(filepath)
