#######################################################
# 複数匹で対戦
#######################################################

from pokejpy.sv.player import *


# ------------------------------

M = 6          # 匹から
N = 3          # 匹選ぶ

# ------------------------------


# 2人のプレイヤーを生成
player = Player()
opponent = Player()

# ポケモンをM匹ずつパーティに追加
for i, pl in enumerate([player, opponent]):
    names = random.sample(list(PokeDB.zukan.keys()), M)
    for j, name in enumerate(names):
        pl.team.append(Pokemon(name))

# パーティの表示
for i, pl in enumerate([player, opponent]):
    for j, p in enumerate(pl.team):
        print(f"Player{i} #{j} {p}\n")
print('-'*50, '\n')

# N匹を選出して対戦
battle = player.game(opponent, n_selection=N)

"""ログ出力、リプレイ
filename = f"random_{N}from{M}.json"
battle.write(filename)
Battle.replay(filename)
"""
