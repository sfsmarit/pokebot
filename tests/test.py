from pokebot import Battle, Player, PokeDB
from pokebot.common.enums import Command


class CustomPlayer(Player):
    def get_selection_commands(self, battle: Battle) -> list[Command]:
        return battle.get_available_selection_commands(self)

    def get_action_command(self, battle: Battle) -> Command:
        return battle.get_available_action_commands(self)[0]


player = CustomPlayer()
player.team.append(PokeDB.create_pokemon("リザードン"))
# player.team[-1].ability = PokeDB.create_ability("いかく")
# player.team[-1].item = PokeDB.create_item("だっしゅつボタン")
# player.team[-1].moves = [PokeDB.create_move("とんぼがえり")]

player.team.append(PokeDB.create_pokemon("ピカチュウ"))
# player.team[-1].moves = [PokeDB.create_move("とんぼがえり")]

for poke in player.team:
    poke.show()

print("-"*50)

opponent = CustomPlayer()
opponent.team.append(PokeDB.create_pokemon("カメックス"))
# opponent.team[-1].ability = PokeDB.create_ability("いかく")
# opponent.team[-1].item = PokeDB.create_item("たべのこし")
opponent.team[-1].moves = [PokeDB.create_move("ふきとばし")]

# opponent.team.append(PokeDB.create_pokemon("フシギバナ"))

for poke in opponent.team:
    poke.show()

print("-"*50)

battle = Battle(player, opponent)

while 1:
    battle.advance_turn()

    print(f"{battle.turn=}")
    for cmd, log in zip(battle.command, battle.get_turn_logs()):
        print(f"\t{cmd}\t{log}")

    if battle.winner() is not None:
        break
