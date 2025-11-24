from copy import deepcopy
from pokebot import Player


player = Player()

d1 = {player: 0}
d2 = deepcopy(d1)

print(player is list(d1.keys())[0])
print(player is list(d2.keys())[0])
