"""
1対1のランダム対戦
"""

import random
from pokebot import PokeDB, Pokemon, Player


# 2人のプレイヤーを生成
player = Player()
opponent = Player()

# 図鑑に登録されているポケモンからランダムに2体選ぶ
names = random.sample(list(PokeDB.zukan.keys()), 2)
player.team.append(Pokemon(names[0]))
opponent.team.append(Pokemon(names[1]))

battle = player.game(opponent)


# ログ出力・リプレイ再生
if True:
    logfile = "./random_battle.json"
    battle.write(logfile)
    player.replay(logfile)
