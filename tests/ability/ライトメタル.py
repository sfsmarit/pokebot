from pokebot import Pokemon, Player, PokeDB


def ライトメタル(display_log: bool = False) -> bool:
    max_turn = 1

    names = [
        ["リザードン"],
        ["カメックス"],
    ]

    abilities = [
        ["ライトメタル"],
        [""],
    ]

    items = [
        [""],
        [""],
    ]

    moves = [
        ["ひっかく"],
        ["はねる"],
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

    # パーティを表示
    if display_log:
        for i, pl in enumerate([player, opponent]):
            for j, p in enumerate(pl.team):
                print(f"Player{i}   #{j} {p}\n")
        print('-'*50)

    poke = player.team[0]
    return poke.weight <= 0.5 * PokeDB.zukan[poke.name].weight


if __name__ == "__main__":
    print(ライトメタル(True))
