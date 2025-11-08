from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..damage_manager import DamageManager

from pokebot.common.enums import Ailment, Weather, Terrain, MoveCategory
from pokebot.common.types import PlayerIndex
import pokebot.common.utils as ut
from pokebot.model import Move
from pokebot.logger.damage_log import DamageLog
from pokebot.core.move_utils import effective_move_type, effective_move_category


def _attack_modifier(self: DamageManager,
                     atk: PlayerIndex | int,
                     move: Move,
                     self_damage: bool,
                     log: DamageLog | None) -> float:

    dfn = atk if self_damage else int(not atk)
    attacker_mgr = self.battle.poke_mgrs[atk]
    attacker = attacker_mgr.pokemon
    defender = self.battle.pokemons[dfn]

    move_type = effective_move_type(self.battle, atk, move)
    move_category = effective_move_category(self.battle, atk, move)

    r = 4096

    # 攻撃側
    if (move_category == MoveCategory.PHY and attacker_mgr.boosted_idx == 1) or \
            (move_category == MoveCategory.SPE and attacker_mgr.boosted_idx == 3):
        r = ut.round_half_up(r*5325/4096)
        if log:
            log.notes.append('ACブースト x1.3')

    r0 = r
    match attacker.ability.name:
        case 'いわはこび':
            if move_type == 'いわ':
                r = ut.round_half_up(r*1.5)
        case 'げきりゅう':
            if move_type == 'みず' and attacker.hp_ratio <= 1/3:
                r = ut.round_half_up(r*1.5)
        case 'ごりむちゅう':
            if move_category == MoveCategory.PHY:
                r = ut.round_half_up(r*1.5)
        case 'こんじょう':
            if attacker.ailment and move_category == MoveCategory.PHY:
                r = ut.round_half_up(r*1.5)
        case 'サンパワー':
            if self.battle.field_mgr.weather(atk) == Weather.SUNNY and move_category == MoveCategory.SPE:
                r = ut.round_half_up(r*1.5)
        case 'しんりょく':
            if move_type == 'くさ' and attacker.hp_ratio <= 1/3:
                r = ut.round_half_up(r*1.5)
        case 'すいほう':
            if move_type == 'みず':
                r = r = ut.round_half_up(r*2)
        case 'スロースタート':
            r = ut.round_half_up(r*0.5)
        case 'ちからもち' | 'ヨガパワー':
            if move_category == MoveCategory.PHY:
                r = ut.round_half_up(r*2)
        case 'トランジスタ':
            if move_type == 'でんき':
                r = ut.round_half_up(r*1.3)
        case 'ねつぼうそう':
            if attacker.ailment == Ailment.BRN and move_category == MoveCategory.SPE:
                r = ut.round_half_up(r*1.5)
        case 'はがねつかい' | 'はがねのせいしん':
            if move_type == 'はがね':
                r = ut.round_half_up(r*1.5)
        case 'ハドロンエンジン':
            if self.battle.field_mgr.terrain() == Terrain.ELEC:
                r = ut.round_half_up(r*5461/4096)
        case 'はりこみ':
            if self.battle.turn_mgr._already_switched[dfn]:
                r = ut.round_half_up(r*2)
        case 'ひひいろのこどう':
            if self.battle.field_mgr.weather(atk) == Weather.SUNNY:
                r = ut.round_half_up(r*5461/4096)
        case 'フラワーギフト':
            if self.battle.field_mgr.weather(atk) == Weather.SUNNY:
                r = ut.round_half_up(r*1.5)
        case 'むしのしらせ':
            if move_type == 'むし' and attacker.hp_ratio <= 1/3:
                r = ut.round_half_up(r*1.5)
        case 'もうか':
            if move_type == 'ほのお' and attacker.hp_ratio <= 1/3:
                r = ut.round_half_up(r*1.5)
        case 'よわき':
            if attacker.hp_ratio <= 1/2:
                r = ut.round_half_up(r*0.5)
        case 'りゅうのあぎと':
            if move_type == 'ドラゴン':
                r = ut.round_half_up(r*1.5)

    if r != r0 and log:
        log.notes.append(f"{attacker.ability} x{r/r0:.1f}")

    if attacker.ability.name == 'もらいび' and attacker.ability.count and move_type == 'ほのお':
        r = ut.round_half_up(r*1.5)
        attacker.ability.count = 0
        if log:
            log.notes.append(f"もらいび x1.5")

    r0 = r
    match attacker.item.name:
        case 'こだわりハチマキ':
            if move_category == MoveCategory.PHY:
                r = ut.round_half_up(r*1.5)
        case 'こだわりメガネ':
            if move_category == MoveCategory.SPE:
                r = ut.round_half_up(r*1.5)
        case 'でんきだま':
            if attacker.name == 'ピカチュウ':
                r = ut.round_half_up(r*2)

    if r != r0 and log:
        log.notes.append(f"{attacker.item} x{r/r0:.1f}")

    # 防御側
    r0 = r
    match self.battle.poke_mgrs[dfn].defending_ability(move).name:
        case 'あついしぼう':
            if move_type in ['ほのお', 'こおり']:
                r = ut.round_half_up(r*0.5)
        case 'きよめのしお':
            if move_type == 'ゴースト':
                r = ut.round_half_up(r*0.5)
        case 'わざわいのうつわ':
            if move_category == MoveCategory.SPE:
                r = ut.round_half_up(r*5072/4096)
        case 'わざわいのおふだ':
            if move_category == MoveCategory.PHY:
                r = ut.round_half_up(r*5072/4096)

    if r != r0 and log:
        log.notes.append(f"{defender.ability} x{r/r0:.2f}")

    return r
