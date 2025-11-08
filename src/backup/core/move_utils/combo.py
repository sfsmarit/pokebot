from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.types import PlayerIndex
# from pokebot.common import PokeDB
from pokebot.model import Move


def num_strikes(battle: Battle,
                atk: PlayerIndex | int,
                move: Move,
                n_default: int | None = None) -> int:
    """(連続)技の発動回数"""
    if move.name not in PokeDB.combo_range:
        return 1

    attacker = battle.pokemons[atk]
    n_min, n_max = PokeDB.combo_range[move.name]

    # 引数で指定された数が適切なら優先する
    if n_default and n_min <= n_default <= n_max:
        return n_default

    if n_min != n_max:
        if attacker.ability.name == 'スキルリンク':
            return n_max
        elif attacker.item.name == 'いかさまダイス':
            return n_max - battle.random.randint(0, 1)
        elif n_min == 2 and n_max == 5:
            return battle.random.choice([2, 2, 2, 3, 3, 3, 4, 5])

    return n_max
