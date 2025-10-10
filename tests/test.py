from pokebot import Battle, Player, PokeDB

player = Player()
player.team.append(PokeDB.create_pokemon("リザードン"))
player.team[-1].ability = PokeDB.create_ability("いかく")
player.team[-1].item = PokeDB.create_item("いのちのたま")
player.team[-1].moves = [PokeDB.create_move("たいあたり")]

player.team.append(PokeDB.create_pokemon("ピカチュウ"))

for poke in player.team:
    poke.show()

print("-"*50)

opponent = Player()
opponent.team.append(PokeDB.create_pokemon("カメックス"))
opponent.team[-1].ability = PokeDB.create_ability("きんちょうかん")
opponent.team[-1].item = PokeDB.create_item("たべのこし")
opponent.team[-1].moves = [PokeDB.create_move("アームハンマー")]

opponent.team.append(PokeDB.create_pokemon("フシギバナ"))

for poke in opponent.team:
    poke.show()

print("-"*50)

battle = Battle(player, opponent)

for _ in range(4):
    battle.advance_turn()
    print(f"{battle.turn=} {[str(cmd) for cmd in battle.commands]}")
    for log in battle.get_turn_logs():
        print(f"\t{log}")
