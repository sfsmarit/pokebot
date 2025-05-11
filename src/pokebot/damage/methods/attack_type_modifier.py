from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..damage_manager import DamageManager

from pokebot.common.types import PlayerIndex
from pokebot.core import Move
from pokebot.logger.damage_log import DamageLog
from pokebot.move import effective_move_type, effective_move_category


def _attack_type_modifier(self: DamageManager,
                          atk: PlayerIndex,
                          move: Move,
                          log: DamageLog | None) -> float:

    attacker_mgr = self.battle.poke_mgr[atk]
    attacker = attacker_mgr.pokemon
    move_type = effective_move_type(self.battle, atk, move)

    r = 1

    if attacker.terastal and move.name != 'テラバースト':
        r0 = r
        if attacker.terastal == 'ステラ' and \
                move_type not in attacker_mgr.consumed_stellar_types:
            if move_type in attacker._types:
                r = r*2.25 if attacker.ability.name == 'てきおうりょく' else r*2.0
            else:
                r *= 1.2
            if log:
                log.notes.append(f"{attacker.terastal}T x{r/r0:.1f}")

        elif move_type == attacker.terastal:
            if attacker.terastal in attacker._types:
                r = r*2.25 if attacker.ability.name == 'てきおうりょく' else r*2.0
            else:
                r = r*2 if attacker.ability.name == 'てきおうりょく' else r*1.5
            if log:
                log.notes.append(f"{attacker.terastal}T x{r/r0:.1f}")

        elif move_type in attacker._types:
            r *= 1.5

    else:
        if move_type in attacker_mgr.types:
            r = r*2 if attacker.ability.name == 'てきおうりょく' else r*1.5

    return r
