from pokebot import Battle, Player, PokeDB

player = Player()
player.team.append(PokeDB.create_pokemon("リザードン"))
player.team[-1].ability = PokeDB.create_ability("いかく")
player.team[-1].item = PokeDB.create_item("いのちのたま")
player.team[-1].moves = [PokeDB.create_move("たいあたり")]
player.team[-1].show()

print("-"*50)

opponent = Player()
opponent.team.append(PokeDB.create_pokemon("カメックス"))
opponent.team[-1].ability = PokeDB.create_ability("かちき")
opponent.team[-1].item = PokeDB.create_item("たべのこし")
opponent.team[-1].moves = [PokeDB.create_move("アームハンマー")]
opponent.team[-1].show()

print("-"*50)

battle = Battle(player, opponent)

for _ in range(2):
    battle.advance_turn()
    print(f"{battle.turn=}")
    for log in battle.get_turn_logs():
        print(f"\t{log}")
