from pokebot import Pokemon, Player, Move
from pokebot.core.move_utils import hit_probability


def すながくれ(display_log: bool = False) -> bool:
    max_turn = 0

    names = [
        ["リザードン"],
        ["カメックス"],
    ]

    abilities = [
        ["すながくれ"],
        ["すなおこし"],
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
    if display_log:
        for i, pl in enumerate([player, opponent]):
            for j, p in enumerate(pl.team):
                print(f"Player{i}   #{j} {p}\n")
        print('-'*50)

    # N匹を選出して対戦
    battle = player.game(opponent, max_turn=max_turn, display_log=display_log, is_test=True)

    r = 0.8
    return r-0.01 < hit_probability(battle, 1, Move("ひっかく")) < r+0.01


if __name__ == "__main__":
    print(すながくれ(True))
