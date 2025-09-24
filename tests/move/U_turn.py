from pokebot import Pokemon, Player, PokeDB, Battle, Move
from pokebot.common.enums import Command
from pokebot.core.move_utils import critical_probability


class CustomPlayer(Player):
    def action_command(self, battle: Battle) -> Command:
        return Command.MOVE_0


def U_turn(display_log: bool = False) -> bool:
    moves = PokeDB.tagged_moves["U_turn"]

    result = True
    for move in moves:
        single_test_result = test(move, display_log)
        if display_log:
            print(f"{move}\t{single_test_result}")
        result &= single_test_result

    return result


def test(move: str, display_log: bool = False) -> bool:
    max_turn = 1

    names = [
        ["リザードン", "ピジョット"],
        ["カメックス", "カメックス"],
    ]

    abilities = [
        ["", ""],
        ["", ""],
    ]

    items = [
        ["", ""],
        ["", ""],
    ]

    moves = [
        [[move], [move]],
        [[""], [""]],
    ]

    # 2人のプレイヤーを生成
    player = CustomPlayer()
    opponent = CustomPlayer()

    # ポケモンをM匹ずつパーティに追加
    for i, pl in enumerate([player, opponent]):
        for j, name in enumerate(names[i]):
            pl.team.append(Pokemon(name))
            pl.team[-1].ability = abilities[i][j]
            pl.team[-1].item = items[i][j]
            pl.team[-1].terastal = ""
            pl.team[-1].moves.clear()
            pl.team[-1].add_moves(moves[i][j])

    # パーティを表示
    if False:
        for i, pl in enumerate([player, opponent]):
            for j, p in enumerate(pl.team):
                print(f"Player{i}   #{j} {p}\n")
        print('-'*50)

    # N匹を選出して対戦
    battle = player.game(opponent, max_turn=max_turn, display_log=display_log)

    if player.team[-1].moves[0].name != move:
        return True

    return "交代" in "".join(battle.logger.get_turn_log(battle.turn, 0))


if __name__ == "__main__":
    print(U_turn(True))
