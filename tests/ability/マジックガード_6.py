from pokebot import Pokemon, Player, PokeDB


def マジックガード_6(display_log: bool = False) -> bool:
    items = [
        "いのちのたま",
        "くろいヘドロ",
    ]
    result = True
    for item in items:
        single_test_result = test(item, display_log)
        if display_log:
            print(f"{item}\t{single_test_result}")
        result &= single_test_result

    return result


def test(item: str, display_log: bool = False) -> bool:
    max_turn = 1

    names = [
        ["ピカチュウ"],
        ["カメックス"],
    ]

    abilities = [
        ["マジックガード"],
        ["ノーガード"],
    ]

    items = [
        [item],
        ["ゴツゴツメット"],
    ]

    moves = [
        ["ひっかく"],
        ["はねる"],
    ]

    terastals = [
        ["ステラ"],
        ["ステラ"],
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
            pl.team[-1].terastal = terastals[i][j]
            pl.team[-1].add_move(moves[i][j])

    # パーティを表示
    if False:
        for i, pl in enumerate([player, opponent]):
            for j, p in enumerate(pl.team):
                print(f"Player{i}   #{j} {p}\n")
        print('-'*50)

    # N匹を選出して対戦
    battle = player.game(opponent, max_turn=max_turn, display_log=display_log)

    return "HP -" not in "".join(battle.logger.get_turn_log(turn=battle.turn, idx=0))


if __name__ == "__main__":
    print(マジックガード_6(True))
