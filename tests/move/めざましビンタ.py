from pokebot import Pokemon, Player, PokeDB
from pokebot.utils.enums import Command, SideField
from pokebot.core.battle import Battle


class CustomPlayer(Player):
    def action_command(self, battle: Battle) -> Command:
        return Command.MOVE_0 if battle.turn == 1 else Command.MOVE_1


def めざましビンタ(display_log: bool = False) -> bool:
    move = "めざましビンタ"
    if move not in PokeDB.move():
        print(f"{move} is not in PokeDB.moves()")
        return True

    max_turn = 2

    names = [
        ["リザードン"],
        ["カメックス"],
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
        [["キノコのほうし", move]],
        [[""]],
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

    return "追加効果" in "".join(battle.logger.get_turn_log(battle.turn, 0))


if __name__ == "__main__":
    print(めざましビンタ(True))
