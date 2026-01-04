import math
from jpoke.utils.test import generate_battle
from jpoke import Pokemon


def test():
    # いのちのたま: 攻撃技で発動
    battle = generate_battle(ally=[Pokemon("ピカチュウ", item="いのちのたま", moves=["たいあたり"])], turn=1)
    assert battle.actives[0].item.revealed
    assert battle.actives[0].hp == math.ceil(battle.actives[0].max_hp * 7/8)
    # いのちのたま: 変化技では発動しない
    battle = generate_battle(ally=[Pokemon("ピカチュウ", item="いのちのたま", moves=["はねる"])], turn=1)
    assert not battle.actives[0].item.revealed

    # だっしゅつボタン
    battle = generate_battle(
        ally=[Pokemon("ピカチュウ", item="だっしゅつボタン"), Pokemon("ライチュウ")],
        foe=[Pokemon("ピカチュウ", moves=["たいあたり"])],
        turn=1,
    )


if __name__ == "__main__":
    test()
