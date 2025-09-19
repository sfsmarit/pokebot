from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..active_pokemon_manager import ActivePokemonManager

import pokebot.common.utils as ut
from pokebot.common import PokeDB
from pokebot.model import Move
from pokebot.logger import TurnLog


def _apply_move_recoil(self: ActivePokemonManager,
                       move: Move,
                       effect: str) -> bool:

    if not PokeDB.get_move_effect_value(move, effect):
        return False

    battle = self.battle

    match effect:
        case 'recoil':
            # 反動
            damage = battle.turn_mgr.damage_dealt[self.idx]

            if not damage or self.pokemon.ability.name == 'いしあたま':
                return False

            recoil = ut.round_half_up(damage * PokeDB.move_effect[move.name]['recoil'])

            if self.add_hp(-recoil):
                battle.logger.insert(-1, TurnLog(battle.turn, self.idx, '反動'))
                return True

        case 'mis_recoil':
            # 技の失敗による反動
            if self.add_hp(ratio=-PokeDB.move_effect[move.name]['mis_recoil']):
                battle.logger.insert(-1, TurnLog(battle.turn, self.idx, '反動'))
                return True

        case 'cost':
            # 発動コスト
            cost = ut.round_half_up(self.pokemon.stats[0] * PokeDB.move_effect[move.name]['cost'])
            if self.add_hp(-cost):
                battle.logger.insert(-1, TurnLog(battle.turn, self.idx, '反動'))
                return True

    return False
