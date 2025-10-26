from copy import deepcopy
from pokebot import Battle, Player, PokeDB
from pokebot.common.enums import Command


class CustomPlayer(Player):
    def choose_selection_commands(self, battle: Battle) -> list[Command]:
        return battle.get_available_selection_commands(self)

    def choose_action_command(self, battle: Battle) -> Command:
        commands = battle.get_available_action_commands(self)
        '''
        copied, copied_player = battle.masked(self)
        copied.advance_turn(commands={copied_player: commands[-1]})
        print(f"(Copied) Turn {copied.turn}")
        for player, log in copied.get_turn_logs().items():
            print(f"\t{player.name}\t{log}")
        '''
        return commands[0]

    def choose_switch_command(self, battle: Battle) -> Command:
        commands = battle.get_available_switch_commands(self)
        # '''
        copied, copied_player = battle.masked(self)
        copied.advance_turn(commands={copied_player: commands[-1]})
        print(f"(Copied) Turn {copied.turn}")
        for player, log in copied.get_turn_logs().items():
            print(f"\t{player.name}\t{log}")
        # '''
        return commands[0]


# ---------------------------------------------------------------------

player = CustomPlayer("Player 1")
player.team.append(PokeDB.create_pokemon("リザードン"))
# player.team[-1].ability = PokeDB.create_ability("かちき")
# player.team[-1].item = PokeDB.create_item("だっしゅつパック")
player.team[-1].moves = [PokeDB.create_move("とんぼがえり")]

player.team.append(PokeDB.create_pokemon("ピカチュウ"))
# player.team[-1].ability = PokeDB.create_ability("いかく")
# player.team[-1].item = PokeDB.create_item("だっしゅつパック")
# player.team[-1].moves = [PokeDB.create_move("アームハンマー")]

player.team.append(PokeDB.create_pokemon("カビゴン"))

# ---------------------------------------------------------------------

rival = Player("Player 2")
rival.team.append(PokeDB.create_pokemon("カメックス"))
# rival.team[-1].ability = PokeDB.create_ability("いかく")
# rival.team[-1].item = PokeDB.create_item("だっしゅつパック")
rival.team[-1].moves = [PokeDB.create_move("アームハンマー")]

# rival.team.append(PokeDB.create_pokemon("フシギバナ"))
# rival.team[-1].ability = PokeDB.create_ability("いかく")
# rival.team[-1].item = PokeDB.create_item("だっしゅつパック")
# rival.team[-1].moves = [PokeDB.create_move("アームハンマー")]

# ---------------------------------------------------------------------

max_turn = 1

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
