from jpoke import Pokemon
from jpoke.utils.test import generate_battle


def test():
    battle = generate_battle(ally=[Pokemon("ピカチュウ", ability="きんちょうかん")])
    assert battle.actives[0].ability.revealed
    assert battle.actives[1].nervous(battle.events)
    assert not battle.actives[0].nervous(battle.events)


if __name__ == "__main__":
    test()
