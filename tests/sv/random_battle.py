from pokejpy.sv.player import *


M = 6                       # 匹から
N = random.randint(1, 6)    # 匹選ぶ

while True:
    # 2人のプレイヤーを生成
    player = MaxDamagePlayer()
    opponent = Player()

    # ポケモンをM匹ずつパーティに追加
    for i, pl in enumerate([player, opponent]):
        # Random name
        names = random.sample(list(PokeDB.zukan.keys()), M)

        for j, name in enumerate(names):
            pl.team.append(Pokemon(name))

            # Random ability
            pl.team[-1].ability = Ability(random.choice(PokeDB.abilities))

            # Random item
            pl.team[-1].item = Item(random.choice(list(PokeDB.items.keys())))

            # Random move
            pl.team[-1].moves.clear()
            pl.team[-1].add_moves(random.sample(list(PokeDB.moves.keys()), random.randint(1, 10)))

    # 表示
    for i, pl in enumerate([player, opponent]):
        for j, p in enumerate(pl.team):
            print(f"Player{i} #{j} {p}\n")
    print('-'*50)

    # N匹を選出して対戦
    battle = player.game(opponent, n_selection=N)

    """ログ出力、リプレイ
    filename = f"random_battle.json"
    battle.write(filename)
    Battle.replay(filename)
    """

    # break
