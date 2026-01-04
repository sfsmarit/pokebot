from jpoke import Battle, Player, Pokemon


PRINT_LOG = True


def generate_battle(ally: list[Pokemon] = [Pokemon("ピカチュウ")],
                    foe: list[Pokemon] = [Pokemon("ピカチュウ")],
                    turn: int = 0) -> Battle:
    players = [Player() for _ in range(2)]
    for player, mons in zip(players, [ally, foe]):
        for mon in mons:
            player.team.append(mon)

    battle = Battle(players)

    while True:
        battle.advance_turn(print_log=PRINT_LOG)
        if battle.winner() or battle.turn == turn:
            return battle
