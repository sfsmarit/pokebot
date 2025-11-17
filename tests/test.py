from copy import deepcopy
from pokebot import Battle, Player, PokeDB
from pokebot.utils.enums import Command


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
        return commands[0] if battle.turn == 1 else commands[-1]

    def choose_switch_command(self, battle: Battle) -> Command:
        commands = battle.get_available_switch_commands(self)
        '''
        copied, copied_player = battle.masked(self)
        copied.advance_turn(commands={copied_player: commands[-1]})
        print(f"(Copied) Turn {copied.turn}")
        for player, log in copied.get_turn_logs().items():
            print(f"\t{player.name}\t{log}")
        '''
        return commands[0]


# ---------------------------------------------------------------------

names = ["リザードン"]
abilities = [""]
items = [""]
move_list = [["すなあらし", "たいあたり"]]

player = CustomPlayer("Player1")
for name, ability, item, moves in zip(names, abilities, items, move_list):
    player.team.append(PokeDB.create_pokemon(name))
    player.team[-1].ability = PokeDB.create_ability(ability)
    player.team[-1].item = PokeDB.create_item(item)
    player.team[-1].moves = [PokeDB.create_move(s) for s in moves]

# ---------------------------------------------------------------------

names = ["フシギバナ"]
abilities = [""]
items = [""]
move_list = [["たいあたり"]]

rival = CustomPlayer("Player2")
for name, ability, item, moves in zip(names, abilities, items, move_list):
    rival.team.append(PokeDB.create_pokemon(name))
    rival.team[-1].ability = PokeDB.create_ability(ability)
    rival.team[-1].item = PokeDB.create_item(item)
    rival.team[-1].moves = [PokeDB.create_move(s) for s in moves]

# ---------------------------------------------------------------------

battle = Battle([player, rival])

# ---------------------------------------------------------------------

max_turn = 6

# ---------------------------------------------------------------------

for pl in battle.players:
    for poke in pl.team:
        print(poke)
    print("-"*50)

# ---------------------------------------------------------------------


while 1:
    battle.advance_turn()

    print(f"Turn {battle.turn}")
    for player, log in battle.get_turn_logs().items():
        print(f"\t{player.name}\t{log}")

    if battle.winner() or battle.turn == max_turn:
        break

battle.export_log("test.json")


exit()

# Replay
print(f"{'='*50}\nReplay\n{'='*50}")

battle = Battle.reconstruct_from_log("test.json")

for pl in battle.players:
    for poke in pl.team:
        print(poke)
    print("-"*50)

while 1:
    battle.advance_turn()

    print(f"Turn {battle.turn}")
    for player, log in battle.get_turn_logs().items():
        print(f"\t{player.name}\t{log}")

    if battle.winner() or battle.turn == max_turn:
        break
