from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..damage_manager import DamageManager

from pokebot.common.constants import TYPE_MODIFIER
from pokebot.common.types import PlayerIndex
from pokebot.model import Move
from pokebot.logger.damage_log import DamageLog
from pokebot.core.move_utils import effective_move_type


def _defence_type_modifier(self: DamageManager,
                           atk: PlayerIndex | int,
                           move: Move,
                           self_damage: bool,
                           log: DamageLog | None) -> float:

    dfn = atk if self_damage else int(not atk)
    attacker = self.battle.pokemons[atk]
    defender = self.battle.pokemons[dfn]
    defender_mgr = self.battle.poke_mgrs[dfn]

    move_type = effective_move_type(self.battle, atk, move)

    r = 1

    if move_type == 'ステラ' and defender.terastal:
        r = 2
    else:
        for t in defender_mgr.types:
            if attacker.ability.name in ['しんがん', 'きもったま'] and \
                    t == 'ゴースト' and move_type in ['ノーマル', 'かくとう']:
                pass
                if log:
                    log.notes.append(attacker.ability.name)
            elif move.name == 'フリーズドライ' and t == 'みず':
                r *= 2
            elif not defender_mgr.is_floating() and move_type == 'じめん' and t == 'ひこう':
                continue
            else:
                r *= TYPE_MODIFIER[move_type][t]
                if move.name == 'フライングプレス':
                    r *= TYPE_MODIFIER['ひこう'][t]
                if r == 0:
                    if defender.item.name == 'ねらいのまと':
                        r = 1
                    else:
                        break

    if (def_ability := defender_mgr.defending_ability(move)) == 'テラスシェル' and \
            r and defender.hp_ratio == 1:
        r = 0.5
        if log:
            log.notes.append(f"{def_ability} x{r:.1f}")

    return r
