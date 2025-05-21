from pokebot import PokeDB, Pokemon, Player
import time
import random

random.seed(1)


M = 6  # 匹から
N = random.randint(1, M)  # 匹選ぶ


item_pool = PokeDB.items()
# item_pool = ["だっしゅつボタン", "だっしゅつパック", "レッドカード"]

ability_pool = PokeDB.abilities

move_pool = list(PokeDB.move_data.keys())


while True:
    # 2人のプレイヤーを生成
    player = Player()
    opponent = Player()

    # ポケモンをM匹ずつパーティに追加
    for i, pl in enumerate([player, opponent]):
        names = random.sample(list(PokeDB.zukan.keys()), M)

        for j, name in enumerate(names):
            pl.team.append(Pokemon(name))
            pl.team[-1].ability = random.choice(ability_pool)
            pl.team[-1].item = random.choice(item_pool)
            pl.team[-1].moves.clear()
            pl.team[-1].add_moves(random.sample(move_pool, random.randint(1, 10)))

    # 表示
    for i, pl in enumerate([player, opponent]):
        for j, p in enumerate(pl.team):
            print(f"Player{i}   #{j} {p}\n")
    print('-'*50)

    # N匹を選出して対戦
    t0 = time.time()
    battle = player.game(opponent, n_selection=N, seed=0)
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

    break
