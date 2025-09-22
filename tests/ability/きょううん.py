from pokebot import Pokemon, Player
from pokebot.common.enums import Command
from pokebot.core.battle import Battle


class CustomPlayer(Player):
    def action_command(self, battle: Battle) -> Command:
        return Command.MOVE_0


def きょううん(display_log: bool = False) -> bool:
    return True

    max_turn = 1

    names = [
        ["リザードン"],
        ["フシギバナ"],
    ]

    abilities = [
        ["きょううん"],
        [""],
    ]

    items = [
        [""],
        [""],
    ]

    moves = [
        ["きりさく"],
        ["はねる"],
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

    return "急所" in battle.logger.get_turn_log(turn=battle.turn, idx=0)


if __name__ == "__main__":
    print(きょううん(True))
