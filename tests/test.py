from pokebot import Battle, Player, PokeDB
from pokebot.common.enums import Command


class CustomPlayer(Player):
    def choose_selection_commands(self, battle: Battle) -> list[Command]:
        return battle.get_available_selection_commands(self)

    def choose_action_command(self, battle: Battle) -> Command:
        return battle.get_available_action_commands(self)[0]


# ---------------------------------------------------------------------

player = CustomPlayer("Player 1")
player.team.append(PokeDB.create_pokemon("リザードン"))
# player.team[-1].ability = PokeDB.create_ability("いかく")
# player.team[-1].item = PokeDB.create_item("だっしゅつパック")
player.team[-1].moves = [PokeDB.create_move("アームハンマー")]

player.team.append(PokeDB.create_pokemon("ピカチュウ"))
# player.team[-1].ability = PokeDB.create_ability("いかく")
# player.team[-1].item = PokeDB.create_item("だっしゅつパック")
player.team[-1].moves = [PokeDB.create_move("アームハンマー")]

# ---------------------------------------------------------------------

rival = CustomPlayer("Player 2")
rival.team.append(PokeDB.create_pokemon("カメックス"))
# rival.team[-1].ability = PokeDB.create_ability("いかく")
# rival.team[-1].item = PokeDB.create_item("だっしゅつパック")
rival.team[-1].moves = [PokeDB.create_move("アームハンマー")]

rival.team.append(PokeDB.create_pokemon("フシギバナ"))
# rival.team[-1].ability = PokeDB.create_ability("いかく")
# rival.team[-1].item = PokeDB.create_item("だっしゅつパック")
rival.team[-1].moves = [PokeDB.create_move("アームハンマー")]

# ---------------------------------------------------------------------

max_turn = 10

# ---------------------------------------------------------------------

for pl in [player, rival]:
    for poke in pl.team:
        print(poke)
    print("-"*50)

# ---------------------------------------------------------------------

battle = Battle([player, rival])

while 1:
    battle.advance_turn()

    print(f"Turn {battle.turn}")
    for player, log in battle.get_turn_logs().items():
        print(f"\t{player.name}\t{log}")

    if battle.winner() or battle.turn == max_turn:
        break
