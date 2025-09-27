from pokebot import Battle, Player, PokeDB

player = Player()
poke = PokeDB.create_pokemon("リザードン")
poke.ability = PokeDB.create_ability("いかく")
poke.item = PokeDB.create_item("いのちのたま")
poke.moves = [PokeDB.create_move("アームハンマー")]
poke.show()
player.team.append(poke)

print("-"*50)

opponent = Player()
poke = PokeDB.create_pokemon("カメックス")
poke.ability = PokeDB.create_ability("かちき")
poke.item = PokeDB.create_item("たべのこし")
poke.moves = [PokeDB.create_move("アームハンマー")]
poke.show()
opponent.team.append(poke)

print("-"*50)

battle = Battle(player, opponent)

for _ in range(2):
    battle.advance_turn()
    print(f"{battle.turn=}")
    for idx in range(2):
        print("\t", battle.logger.get_turn_logs(battle.turn)[idx])
