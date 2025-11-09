from pokebot import Pokemon, Player, PokeDB
from pokebot.utils.enums import Command
from pokebot.core.battle import Battle


class CustomPlayer(Player):
    def action_command(self, battle: Battle) -> Command:
        return Command.MOVE_0


def critical(display_log: bool = False) -> bool:
    result = True
    for move in PokeDB.tagged_moves["critical"]:
        single_test_result = test(move, display_log)
        if display_log:
            print(f"{move}\t{single_test_result}")
        result &= single_test_result

    return result


def test(move: str, display_log: bool = False) -> bool:
    max_turn = 1

    names = [
        ["リザードン"],
        ["ガルーラ"],
    ]

    abilities = [
        [""],
        ["ノーガード"],
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

    if player.team[-1].moves[0].name != move:
        return True

    return f"急所" in "".join(battle.logger.get_damage_log(turn=battle.turn, idx=0))


if __name__ == "__main__":
    print(critical(True))
