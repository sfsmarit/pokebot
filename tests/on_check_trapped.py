from jpoke import Pokemon
from jpoke.utils.test import generate_battle


SHOW_LOG = True


def check_switch(battle, idx=1) -> bool:
    """交代可能ならTrueを返す"""
    commands = battle.get_available_action_commands(battle.players[idx])
    return any(c.is_switch() for c in commands)


def test():
    # ニュートラル
    assert check_switch(
        generate_battle(
            foe=[Pokemon("ピカチュウ") for _ in range(2)]
        )
    )
    # ありじごく
    assert not check_switch(
        generate_battle(
            ally=[Pokemon("ピカチュウ", ability="ありじごく")],
            foe=[Pokemon("ピカチュウ") for _ in range(2)]
        )
    )
    # ありじごくは飛行タイプに無効
    assert check_switch(
        generate_battle(
            ally=[Pokemon("ピカチュウ", ability="ありじごく")],
            foe=[Pokemon("リザードン") for _ in range(2)]
        )
    )
    # ゴーストタイプには無効
    assert check_switch(
        generate_battle(
            ally=[Pokemon("ピカチュウ", ability="ありじごく")],
            foe=[Pokemon("ゲンガー") for _ in range(2)]
        )
    )

    # かげふみ
    assert not check_switch(
        generate_battle(
            ally=[Pokemon("ピカチュウ", ability="かげふみ")],
            foe=[Pokemon("ピカチュウ") for _ in range(2)]
        )
    )
    # かげふみ相手にかげふみ無効
    assert check_switch(
        generate_battle(
            ally=[Pokemon("ピカチュウ", ability="かげふみ")],
            foe=[Pokemon("ピカチュウ", ability="かげふみ") for _ in range(2)]
        )
    )

    # じりょく
    assert not check_switch(
        generate_battle(
            ally=[Pokemon("ピカチュウ", ability="じりょく")],
            foe=[Pokemon("ハッサム") for _ in range(2)]
        )
    )
    # じりょくははがねタイプ以外には無効
    assert check_switch(
        generate_battle(
            ally=[Pokemon("ピカチュウ", ability="じりょく")],
            foe=[Pokemon("ピカチュウ") for _ in range(2)]
        )
    )

    # きれいなぬけがら
    assert check_switch(
        generate_battle(
            ally=[Pokemon("ピカチュウ", ability="かげふみ")],
            foe=[Pokemon("ピカチュウ", item="きれいなぬけがら") for _ in range(2)]
        )
    )


if __name__ == "__main__":
    test()
