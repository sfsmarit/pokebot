from pokebot import Pokemon, Player
from pokebot.common.enums import Command
from pokebot.core.battle import Battle


class CustomPlayer(Player):
    def action_command(self, battle: Battle) -> Command:
        return Command.MOVE_0


def エレクトロビーム(display_log: bool = False) -> bool:
    moves = ["エレクトロビーム"]
    abilities = ["あめふらし"]

    result = True
    for move, ability in zip(moves, abilities):
        single_test_result = test(move, ability, display_log)
        if display_log:
            print(f"{move}\t{single_test_result}")
        result &= single_test_result

    return result


def test(move: str, ability: str, display_log: bool = False) -> bool:
    max_turn = 1

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
        [[move]],
        [["はねる"]],
    ]

    # 2人のプレイヤーを生成
    player = CustomPlayer()
    opponent = Player()

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

    return all(s in "".join(battle.logger.get_turn_log(turn=battle.turn, idx=0)) for s in ["C+1", "ダメージ"])


if __name__ == "__main__":
    print(エレクトロビーム(True))
