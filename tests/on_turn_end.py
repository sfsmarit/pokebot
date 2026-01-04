from jpoke import Pokemon
from jpoke.utils.test import generate_battle, PRINT_LOG


def test():
    # たべのこし
    mon = Pokemon("ピカチュウ", item="たべのこし")
    battle = generate_battle(ally=[mon], turn=0)
    mon.hp = 1
    battle.advance_turn(print_log=PRINT_LOG)
    assert battle.actives[0].item.observed
    assert battle.actives[0].hp == 1 + mon.max_hp // 16


if __name__ == "__main__":
    test()
