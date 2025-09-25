from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..damage_manager import DamageManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import SideField, MoveCategory
import pokebot.common.utils as ut
from pokebot.pokedb import Move
from pokebot.logger.damage_log import DamageLog
from pokebot.core.move_utils import effective_move_type, effective_move_category


def _damage_modifier(self: DamageManager,
                     atk: PlayerIndex | int,
                     move: Move,
                     self_damage: bool,
                     is_lethal: bool,
                     log: DamageLog | None) -> float:

    dfn = atk if self_damage else int(not atk)
    attacker = self.battle.pokemons[atk]
    defender = self.battle.pokemons[dfn]
    defender_mgr = self.battle.poke_mgrs[dfn]

    move_type = effective_move_type(self.battle, atk, move)
    move_category = effective_move_category(self.battle, atk, move)

    r = 4096
    r_defence_type = self.battle.damage_mgr.defence_type_modifier(atk, move, log=log)

    r0 = r
    match move.name:
        case 'アクセルブレイク' | 'イナズマドライブ':
            if r_defence_type > 1:
                r = ut.round_half_up(r*5461/4096)
        case 'じしん' | 'マグニチュード':
            if defender_mgr.hidden and defender_mgr.executed_move.name == 'あなをほる':
                r *= 2
        case 'なみのり':
            if defender_mgr.hidden and defender_mgr.executed_move.name == 'ダイビング':
                r *= 2

    if r != r0 and log:
        log.notes.append(f"{move} x{r/r0:.2f}")

    # 攻撃側の特性
    match attacker.ability.name:
        case 'いろめがね':
            if r_defence_type < 1:
                r *= 2
        case 'スナイパー':
            if self.critical:
                r = ut.round_half_up(r*1.5)

    if r != r0 and log:
        log.notes.append(f"{attacker.ability} x{r/r0:.2f}")

    # 防御側の特性
    r0 = r
    match defender_mgr.defending_ability(move).name:
        case 'かぜのり':
            if "wind" in move.tags:
                r = 0
        case 'こおりのりんぷん':
            if move_category == MoveCategory.SPE:
                r = ut.round_half_up(r*0.5)
        case 'こんがりボディ':
            if move_type == 'ほのお':
                r = 0
        case 'そうしょく':
            if move_type == 'くさ':
                r = 0
        case 'ちくでん' | 'でんきエンジン' | 'ひらいしん':
            if move_type == 'でんき':
                r = 0
        case 'ちょすい' | 'よびみず':
            if move_type == 'みず':
                r = 0
        case 'どしょく':
            if move_type == 'じめん':
                r = 0
        case 'ハードロック':
            if self.battle.damage_mgr.defence_type_modifier(atk, move) > 1:
                r = ut.round_half_up(r*0.75)
        case 'パンクロック':
            if "sound" in move.tags:
                r = ut.round_half_up(r*0.5)
        case 'フィルター' | 'プリズムアーマー':
            if self.battle.damage_mgr.defence_type_modifier(atk, move) > 1:
                r = ut.round_half_up(r*5072/4096)
        case 'ぼうおん':
            if "sound" in move.tags:
                r = 0
        case 'ぼうだん':
            if "bullet" in move.tags:
                r = 0
        case 'ファントムガード' | 'マルチスケイル':
            if not is_lethal and defender.hp_ratio == 1:
                r = ut.round_half_up(r*0.5)
        case 'もふもふ':
            if move_type == 'ほのお':
                r = ut.round_half_up(r*2)
            elif "contact" in move.tags:
                r = ut.round_half_up(r*0.5)
        case 'もらいび':
            if move_type == 'ほのお':
                r = 0

    if r != r0 and log:
        log.notes.append(f"{defender.ability} x{r/r0:.2f}")
        self.battle.turn_mgr._move_was_negated_by_ability = True

    # 攻撃側のアイテム
    r0 = r
    match attacker.item.name:
        case 'いのちのたま':
            r = ut.round_half_up(r*5324/4096)
        case 'たつじんのおび':
            if r_defence_type > 1:
                r = ut.round_half_up(r*4915/4096)

    if r != r0 and log:
        log.notes.append(f"{attacker.item} x{r/r0:.1f}")

    # 壁
    r0 = r
    if not self.critical and \
            attacker.ability.name != 'すりぬけ' and \
            "wall_break" in move.tags and \
            ((self.battle.field_mgr.count[SideField.REFLECTOR][dfn] and move_category == MoveCategory.PHY) or
             (self.battle.field_mgr.count[SideField.LIGHT_WALL][dfn] and move_category == MoveCategory.SPE)):
        r = ut.round_half_up(r*0.5)

    if r != r0 and log:
        log.notes.append(f"壁 x{r/r0:.1f}")

    # 粉技無効
    r0 = r
    if "powder" in move.tags:
        if defender_mgr.is_overcoat(move):
            r = 0
        elif move.name != 'わたほうし' and 'くさ' in defender_mgr.types:
            r = 0

    if r != r0 and log:
        log.notes.append(f"粉わざ無効 x{r/r0:.1f}")

    if move_type == 'じめん' and defender_mgr.is_floating():
        r = 0

    if r != r0 and log:
        log.notes.append(f"浮遊 x{r/r0:.1f}")

    # 半減実
    r0 = r
    if move.power and defender.item.debuff_type == move_type and \
            not defender_mgr.is_nervous() and \
            (move_type == 'ノーマル' or r_defence_type > 1):
        r = ut.round_half_up(r*0.5)

    if r != r0 and log:
        log.notes.append(f"{defender.item} x{r/r0:.1f}")
        log.item_consumed[dfn] = True

    return r
