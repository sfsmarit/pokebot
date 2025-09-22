from pokebot import Pokemon, Player
from pokebot.common.enums import Phase


def ありじごく(display_log: bool = False) -> bool:
    abilities = ["ありじごく", "かげふみ", "じりょく"]
    result = True
    for ability in abilities:
        single_test_result = test(ability, display_log)
        if display_log:
            print(f"{ability}\t{single_test_result}")
        result &= single_test_result

    return result


def test(ability: str, display_log: bool = False) -> bool:
    max_turn = 0

    names = [
        ["ピカチュウ", "ピカチュウ"],
        ["ハガネール", "ハガネール"],
    ]

    abilities = [
        [ability, ability],
        ["", ""],
    ]

    items = [
        ["", ""],
        ["", ""],
    ]

    moves = [
        ["はねる", "はねる"],
        ["はねる", "はねる"],
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
    if False:
        for i, pl in enumerate([player, opponent]):
            for j, p in enumerate(pl.team):
                print(f"Player{i}   #{j} {p}\n")
        print('-'*50)

    # N匹を選出して対戦
    battle = player.game(opponent, max_turn=max_turn, display_log=display_log, is_test=True)

    return not any([cmd.is_switch for cmd in battle.available_commands(1, phase=Phase.ACTION)])


if __name__ == "__main__":
    print(ありじごく(True))
