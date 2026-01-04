from jpoke import Pokemon
from jpoke.utils.test import generate_battle


def test():
    battle = generate_battle(ally=[Pokemon("ピカチュウ", ability="いかく")])
    assert battle.actives[0].ability.observed
    assert battle.actives[1].field_status.rank["A"] == -1

    battle = generate_battle(ally=[Pokemon("ピカチュウ", ability="きんちょうかん")])
    assert battle.actives[0].ability.observed

    battle = generate_battle(ally=[Pokemon("ピカチュウ", ability="ぜったいねむり")])
    assert battle.actives[0].ability.observed
    assert battle.actives[0].ailment == "ねむり"

    battle = generate_battle(ally=[Pokemon("ピカチュウ", ability="グラスメイカー")])
    assert battle.actives[0].ability.observed
    assert battle.field.fields["terrain"] == "グラスフィールド"


if __name__ == "__main__":
    test()
