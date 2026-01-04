from jpoke.utils.test import generate_battle
from jpoke import Pokemon


def test():
    # だっしゅつボタン
    battle = generate_battle(
        ally=[Pokemon("ピカチュウ", item="だっしゅつボタン"), Pokemon("ライチュウ")],
        foe=[Pokemon("ピカチュウ", moves=["たいあたり"])],
        turn=1,
    )
    assert battle.players[0].active_idx != 0
    assert battle.players[0].team[0].item.revealed
    assert not battle.players[0].team[0].item.active


if __name__ == "__main__":
    test()
