from pokebot import Pokemon, Player, PokeDB, Move
from pokebot.core.move_utils import hit_probability


def しょうりのほし(display_log: bool = False) -> bool:
    abilities = ["しょうりのほし", "ふくがん"]
    ratios = [1.1, 1.3]
    result = True
    for ability, ratio in zip(abilities, ratios):
        single_test_result = test(ability, ratio, display_log)
        if display_log:
            print(f"{ability}\t{single_test_result}")
        result &= single_test_result

    return result


def test(ability: str, ratio: float, display_log: bool = False) -> bool:
    max_turn = 0

    names = [
        ["リザードン"],
        ["カメックス"],
    ]

    abilities = [
        [ability],
        [""],
    ]

    items = [
        [""],
        [""],
    ]

    moves = [
        ["はねる"],
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
    if False:
        for i, pl in enumerate([player, opponent]):
            for j, p in enumerate(pl.team):
                print(f"Player{i}   #{j} {p}\n")
        print('-'*50)

    # N匹を選出して対戦
    battle = player.game(opponent, max_turn=max_turn, display_log=display_log, is_test=True)

    move = Move("でんじほう")
    hit = PokeDB.move_data[move.name].hit / 100
    return hit*(ratio-0.01) < hit_probability(battle, 0, move) < hit*(ratio+0.01)


if __name__ == "__main__":
    print(しょうりのほし(True))
