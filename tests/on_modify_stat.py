from jpoke import Pokemon
from jpoke.utils.test import generate_battle


def test():
    # かちき
    battle = generate_battle(ally=[Pokemon("ピカチュウ", ability="かちき")])
    battle.modify_stat(battle.actives[0], "A", -1, by_foe=True)
    assert battle.actives[0].ability.revealed
    assert battle.actives[0].field_status.rank["C"] == 2

    # かちき : 相手による能力ダウンでなければ発動しない
    battle = generate_battle(ally=[Pokemon("ピカチュウ", ability="かちき")])
    battle.modify_stat(battle.actives[0], "A", -1, by_foe=False)
    assert not battle.actives[0].ability.revealed
    assert battle.actives[0].field_status.rank["C"] == 0

    # かちき : 相手のいかくにより発動
    battle = generate_battle(
        ally=[Pokemon("ピカチュウ", ability="かちき")],
        foe=[Pokemon("ピカチュウ", ability="いかく")]
    )
    assert battle.actives[0].ability.revealed

    # だっしゅつパック
    battle = generate_battle(
        ally=[Pokemon("ピカチュウ", item="だっしゅつパック"), Pokemon("ライチュウ")],
        foe=[Pokemon("ピカチュウ", ability="いかく")],
    )
    assert battle.players[0].active_idx != 0
    assert battle.players[0].team[0].item.revealed
    assert not battle.players[0].team[0].item.active

    # だっしゅつパック : 能力上昇では発動しない
    battle = generate_battle(
        ally=[Pokemon("ピカチュウ", item="だっしゅつパック", moves=["つるぎのまい"]), Pokemon("ライチュウ")],
        turn=1,
    )
    assert not battle.players[0].team[0].item.revealed


if __name__ == "__main__":
    test()
