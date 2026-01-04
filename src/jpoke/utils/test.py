from jpoke import Battle, Player, Pokemon
from jpoke.utils.enums import Command


class CustomPlayer(Player):
    def choose_selection_commands(self, battle: Battle) -> list[Command]:
        return battle.get_available_selection_commands(self)

    def choose_action_command(self, battle: Battle) -> Command:
        return battle.get_available_action_commands(self)[0]


PRINT_LOG = True


def generate_battle(ally: list[Pokemon] = [Pokemon("ピカチュウ")],
                    foe: list[Pokemon] = [Pokemon("ピカチュウ")],
                    turn: int = 0,
                    ) -> Battle:
    players = [CustomPlayer() for _ in range(2)]
    for player, mons in zip(players, [ally, foe]):
        for mon in mons:
            player.team.append(mon)

    battle = Battle(players)  # type: ignore

    while True:
        battle.advance_turn(print_log=PRINT_LOG)
        if battle.winner() or battle.turn == turn:
            return battle
