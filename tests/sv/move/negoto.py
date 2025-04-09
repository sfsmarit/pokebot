from pokejpy.sv.battle import *


def simple_pokemon(name: str):
    p = Pokemon(name)
    p.Ability = Ability()
    p.item = Item()
    p.Ttype = None
    return p


player, opponent = Player(), Player()

p = simple_pokemon('ヒトカゲ')
p.moves = [Move('キノコのほうし')]
player.team.append(p)

p = simple_pokemon('ゼニガメ')
p.moves = [Move('ねごと'), Move('たいあたり')]
opponent.team.append(p)

# パーティの表示
for i, pl in enumerate([player, opponent]):
    for j, p in enumerate(pl.team):
        print(f"Player{i} #{j} {p}\n")
print('-'*50, '\n')

player.game(opponent, max_turn=3)
