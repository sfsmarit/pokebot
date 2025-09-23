from pokebot import Pokemon, Player


def マジックガード_1(display_log: bool = False) -> bool:
    max_turn = 2

    names = [
        ["ピカチュウ"],
        ["カメックス"],
    ]

    abilities = [
        ["マジックガード"],
        [""],
    ]

    items = [
        ["かえんだま"],
        [""],
    ]

    moves = [
        ["はねる"],
        ["はねる"],
    ]

    terastals = [
        ["ほのお"],
        ["みず"],
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
    if display_log:
        for i, pl in enumerate([player, opponent]):
            for j, p in enumerate(pl.team):
                print(f"Player{i}   #{j} {p}\n")
        print('-'*50)

    # N匹を選出して対戦
    battle = player.game(opponent, max_turn=max_turn, display_log=display_log)

    return "やけど" not in "".join(battle.logger.get_turn_log(turn=battle.turn, idx=0))


if __name__ == "__main__":
    print(マジックガード_1(True))
