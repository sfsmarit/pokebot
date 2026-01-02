from jpoke import Battle, Player, PokeDB


SHOW_LOG = True


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


def advance_turn(battle, max_turn=None):
    while True:
        battle.advance_turn()
        if SHOW_LOG:
            turn_logs = battle.get_turn_logs()
            damage_logs = battle.get_damage_logs()
            print(f"Turn {battle.turn}")
            for player in battle.players:
                print(f"\t{player.name}\t{turn_logs[player]} {damage_logs[player]}")
        if battle.winner() or battle.turn == max_turn:
            return


def setup_battle(
    ability,
    ally=["ピカチュウ"],
    foe=["ピカチュウ"],
):
    name_lists = [ally, foe]
    ability_lists = [
        [ability],
        [""]*len(name_lists[0]),
    ]
    battle = generate_battle(name_lists, ability_lists)
    advance_turn(battle, max_turn=0)
    return battle


def test():
    battle = setup_battle("いかく")
    assert battle.actives[0].ability.observed
    assert battle.actives[1].field_status.rank[1] == -1

    battle = setup_battle("きんちょうかん")
    assert battle.actives[0].ability.observed

    battle = setup_battle("ぜったいねむり")
    assert battle.actives[0].ability.observed
    assert battle.actives[0].ailment == "ねむり"

    battle = setup_battle("グラスメイカー")
    assert battle.actives[0].ability.observed
    assert battle.field.fields["terrain"] == "グラスフィールド"


if __name__ == "__main__":
    test()
