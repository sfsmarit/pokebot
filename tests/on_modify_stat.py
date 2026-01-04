from jpoke import Pokemon
from jpoke.utils.test import generate_battle


def test():
    # かちき発動
    battle = generate_battle(ally=[Pokemon("ピカチュウ", ability="かちき")])
    battle.modify_stat(battle.actives[0], "A", -1, by_foe=True)
    assert battle.actives[0].ability.observed
    assert battle.actives[0].field_status.rank["C"] == 2

    # 相手による能力ダウンでなければかちきは発動しない
    battle = generate_battle(ally=[Pokemon("ピカチュウ", ability="かちき")])
    battle.modify_stat(battle.actives[0], "A", -1, by_foe=False)
    assert not battle.actives[0].ability.observed
    assert battle.actives[0].field_status.rank["C"] == 0

    # 相手のいかくによりかちき発動
    battle = generate_battle(
        ally=[Pokemon("ピカチュウ", ability="かちき")],
        foe=[Pokemon("ピカチュウ", ability="いかく")]
    )
    assert battle.actives[0].ability.observed


if __name__ == "__main__":
    test()
