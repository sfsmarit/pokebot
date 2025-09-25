from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Ailment, Condition
from pokebot.pokedb import Move


def critical_probability(battle: Battle,
                         atk: PlayerIndex | int,
                         move: Move) -> float:
    dfn = not atk
    attacker_mgr = battle.poke_mgrs[atk]
    attacker = attacker_mgr.pokemon
    defender = battle.pokemons[dfn]

    # 急所無効
    if battle.poke_mgrs[dfn].defending_ability(move).name in ['シェルアーマー', 'カブトアーマー'] or \
            "one_ko" in move.tags:
        return 0.

    m = attacker_mgr.count[Condition.CRITICAL]

    match attacker.ability.name:
        case 'きょううん':
            m += 1
        case 'ひとでなし':
            if defender.ailment == Ailment.PSN:
                m += 3

    if attacker.item.name in ['するどいツメ', 'ピントレンズ']:
        m += 1

    if "critical" in move.tags:
        m += 3
    elif "high_critical" in move.tags:
        m += 1

    return 1/24*(m == 0) + 0.125*(m == 1) + 0.5*(m == 2) + 1*(m >= 3)
