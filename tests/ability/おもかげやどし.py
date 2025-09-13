from pokebot import Pokemon, Player


max_turn = 3


names = [
    ["オーガポン(みどり)"],
    ["オーガポン(かまど)"],
]

abilities = [
    [""],
    [""],
]

items = [
    [""],
    [""],
]

moves = [
    ["ひっかく"],
    ["ひっかく"],
]

# 2人のプレイヤーを生成
player = Player()
opponent = Player()

# ポケモンをM匹ずつパーティに追加
for i, pl in enumerate([player, opponent]):
    for j, name in enumerate(names[i]):
        pl.team.append(Pokemon(name))
        pl.team[-1].ability = abilities[i][j]
        pl.team[-1].item = items[i][j]
        pl.team[-1].moves.clear()
        pl.team[-1].add_move(moves[i][j])

# 表示
for i, pl in enumerate([player, opponent]):
    for j, p in enumerate(pl.team):
        print(f"Player{i}   #{j} {p}\n")
print('-'*50)

# N匹を選出して対戦
battle = player.game(opponent, seed=0, max_turn=max_turn)
