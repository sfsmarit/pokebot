from copy import deepcopy
from jpoke import Battle, Player, PokeDB
from jpoke.utils.enums import Command


# ---------------------------------------------------------------------

names = ["リザードン", "ピカチュウ"]
abilities = [""]
items = [""]
move_list = [["たいあたり"], ["たいあたり"],]

player = Player("Player1")
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

rival = Player("Player2")
for name, ability, item, moves in zip(names, abilities, items, move_list):
    rival.team.append(PokeDB.create_pokemon(name))
    rival.team[-1].ability = PokeDB.create_ability(ability)
    rival.team[-1].item = PokeDB.create_item(item)
    rival.team[-1].moves = [PokeDB.create_move(s) for s in moves]

# ---------------------------------------------------------------------

battle = Battle([player, rival])
battle.advance_turn()
