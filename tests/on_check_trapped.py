from jpoke import Battle, Player, PokeDB
from jpoke.utils.enums import Command


def generate_battle(name_lists, ability_lists=None, item_lists=None, move_lists=None):
    if not ability_lists:
        ability_lists = [[""]*len(name_lists[i]) for i in range(2)]
    if not item_lists:
        item_lists = [[""]*len(name_lists[i]) for i in range(2)]
    if not move_lists:
        move_lists = [["はねる"]*len(name_lists[i]) for i in range(2)]

    players = [Player() for _ in range(2)]
    for player, names, abilities, items, moves in \
            zip(players, name_lists, ability_lists, item_lists, move_lists):
        for name, ability, item, move in zip(names, abilities, items, moves):
            player.team.append(PokeDB.create_pokemon(name))
            player.team[-1].ability = PokeDB.create_ability(ability)
            player.team[-1].item = PokeDB.create_item(item)
            player.team[-1].moves = [PokeDB.create_move(move)]
    return Battle(players)


def advance_turn(battle, max_turn=None, log=False):
    while True:
        battle.advance_turn()
        if log:
            turn_logs = battle.get_turn_logs()
            damage_logs = battle.get_damage_logs()
            print(f"Turn {battle.turn}")
            for player in battle.players:
                print(f"\t{player.name}\t{turn_logs[player]} {damage_logs[player]}")
        if battle.winner() or battle.turn == max_turn:
            return


def check_switch(
    catcher_ability="",
    escapee_ability="",
    escapee_item="",
    catcher=["ピカチュウ"],
    escapees=["ピカチュウ"]*2,
) -> bool:
    """交代可能ならTrueを返す"""
    name_lists = [catcher, escapees]
    ability_lists = [[catcher_ability], [escapee_ability]*2]
    item_lists = [[""], [escapee_item]*2]
    battle = generate_battle(name_lists, ability_lists, item_lists)
    advance_turn(battle, max_turn=0)
    commands = battle.get_available_action_commands(battle.players[1])
    can_switch = any(c.is_switch() for c in commands)
    return can_switch


def test():
    assert True == check_switch()
    assert False == check_switch("ありじごく")
    assert True == check_switch("ありじごく", escapees=["リザードン"]*2)
    assert True == check_switch("ありじごく", escapees=["ゲンガー"]*2)
    assert False == check_switch("かげふみ")
    assert True == check_switch("かげふみ", escapee_ability="かげふみ")
    assert False == check_switch("じりょく", escapees=["ハッサム"]*2)
    assert True == check_switch("じりょく")

    assert True == check_switch("かげふみ", escapee_item="きれいなぬけがら")


if __name__ == "__main__":
    test()
