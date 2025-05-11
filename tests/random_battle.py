from pokebot import PokeDB, Pokemon, RandomPlayer
import time
import random

random.seed(1)


M = 6  # 匹から
N = random.randint(1, M)  # 匹選ぶ

while True:
    # 2人のプレイヤーを生成
    player = RandomPlayer()
    opponent = RandomPlayer()

    # ポケモンをM匹ずつパーティに追加
    for i, pl in enumerate([player, opponent]):
        names = random.sample(list(PokeDB.zukan.keys()), M)

        for j, name in enumerate(names):
            pl.team.append(Pokemon(name))
            pl.team[-1].ability = random.choice(PokeDB.abilities)
            pl.team[-1].item = random.choice(list(PokeDB.item_data.keys()))
            pl.team[-1].moves.clear()
            pl.team[-1].add_moves(random.sample(list(PokeDB.moves.keys()),
                                                random.randint(1, 10)))

    # 表示
    for i, pl in enumerate([player, opponent]):
        for j, p in enumerate(pl.team):
            print(f"Player{i}   #{j} {p}\n")
    print('-'*50)

    # N匹を選出して対戦
    t0 = time.time()
    battle = player.game(opponent, n_selection=N, seed=0)
    print(f"{time.time() - t0:.2f}s")

    # リプレイ
    if False:
        # ログ出力
        filepath = f"tests/random_battle.json"
        battle.write(filepath)
        # リプレイ再生
        print(f"\n{'-'*50}\nリプレイ {filepath}\n{'-'*50}")
        player.replay(filepath)

    # break
