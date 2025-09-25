from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..damage_manager import DamageManager

from pokebot.common.enums import MoveCategory, Weather, Terrain
from pokebot.common.types import PlayerIndex
import pokebot.common.utils as ut
from pokebot.pokedb import Move
from pokebot.logger.damage_log import DamageLog
from pokebot.core.move_utils import effective_move_type, effective_move_category


def _defence_modifier(self: DamageManager,
                      atk: PlayerIndex | int,
                      move: Move,
                      self_damage: bool,
                      log: DamageLog | None) -> float:

    dfn = atk if self_damage else int(not atk)
    attacker = self.battle.pokemons[atk]
    defender_mgr = self.battle.poke_mgrs[dfn]
    defender = defender_mgr.pokemon

    move_type = effective_move_type(self.battle, atk, move)
    move_category = effective_move_category(self.battle, atk, move)

    r = 4096

    # 攻撃側
    r0 = r
    match attacker.ability.name:
        case 'わざわいのたま':
            if move_category == MoveCategory.SPE and "physical" not in move.tags:
                r = ut.round_half_up(r*5072/4096)
        case 'わざわいのつるぎ':
            if move_category == MoveCategory.PHY or "physical" in move.tags:
                r = ut.round_half_up(r*5072/4096)

    if r != r0 and log:
        log.notes.append(f"{attacker.ability} x{r0/r:.2f}")

    # 防御側
    if ((move_category == MoveCategory.PHY or "physical" in move.tags) and defender_mgr.boosted_idx == 2) or \
            (move_category == MoveCategory.SPE and "physical" not in move.tags and defender_mgr.boosted_idx == 4):
        r = ut.round_half_up(r*5325/4096)
        if log:
            log.notes.append('BDブースト x0.77')

    r0 = r
    match defender.item.name:
        case 'しんかのきせき':
            if True:
                r = ut.round_half_up(r*1.5)
        case 'とつげきチョッキ':
            if move_category == MoveCategory.SPE and "physical" not in move.tags:
                r = ut.round_half_up(r*1.5)

    if r != r0 and log:
        log.notes.append(f"{defender.item} x{r0/r:.2f}")

    r0 = r
    match self.battle.poke_mgrs[dfn].defending_ability(move).name:
        case 'くさのけがわ':
            if self.battle.field_mgr.terrain(dfn) == Terrain.GRASS and \
                    (move_category == MoveCategory.PHY or "physical" in move.tags):
                r = ut.round_half_up(r*1.5)
        case 'すいほう':
            if move_type == 'ほのお':
                r = ut.round_half_up(r*2)
        case 'ファーコート':
            if move_category == MoveCategory.PHY or "physical" in move.tags:
                r = ut.round_half_up(r*2)
        case 'ふしぎなうろこ':
            if defender.ailment and (move_category == MoveCategory.PHY or "physical" in move.tags):
                r = ut.round_half_up(r*1.5)
        case 'フラワーギフト':
            if self.battle.field_mgr.weather(dfn) == Weather.SUNNY:
                r = ut.round_half_up(r*1.5)

    if r != r0 and log:
        log.notes.append(f"{defender.ability} x{r0/r:.2f}")

    return r
