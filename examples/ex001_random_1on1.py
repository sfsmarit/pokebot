#######################################################
# タイマン勝負
#######################################################

from pokejpy.sv.battle import *


# 対戦させるポケモン
name1, name2 = random.sample(list(PokeDB.zukan.keys()), 2)

# 2人のプレイヤーを生成
player = Player()
opponent = Player()

# ポケモンを1匹ずつパーティに追加
player.team.append(Pokemon(name1))
opponent.team.append(Pokemon(name2))

# パーティの表示
for i, pl in enumerate([player, opponent]):
    for j, p in enumerate(pl.team):
        print(f"Player{i} #{j} {p}\n")
print('-'*50, '\n')

# 対戦
battle = player.game(opponent)

"""ログ出力、リプレイ
filename = "random_1on1.json"
battle.write(filename)
Battle.replay(filename)
"""
