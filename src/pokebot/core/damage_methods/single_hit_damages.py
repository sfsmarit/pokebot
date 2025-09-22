from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..damage_manager import DamageManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import MoveCategory, Ailment, Weather
import pokebot.common.utils as ut
from pokebot.model import Move

from pokebot.core.move_utils import effective_move_category, effective_move_type


def _single_hit_damages(self: DamageManager,
                        atk: PlayerIndex | int,
                        move: Move,
                        power_multiplier: float,
                        self_damage: bool,
                        lethal_calc: bool) -> list[int]:

    if move.power == 0:
        return [0]

    dfn = atk if self_damage else int(not atk)
    attacker_mgr = self.battle.poke_mgrs[atk]
    defender_mgr = self.battle.poke_mgrs[dfn]
    attacker = attacker_mgr.pokemon
    defender = defender_mgr.pokemon

    move_type = effective_move_type(self.battle, atk, move)
    move_category = effective_move_category(self.battle, atk, move)

    # 補正値
    r_attack_type = self.attack_type_modifier(atk, move, log=self.log)
    r_defence_type = self.defence_type_modifier(atk, move, self_damage=self_damage, log=self.log)
    r_power = self.power_modifier(atk, move, self_damage=self_damage, log=self.log)
    r_attack = self.attack_modifier(atk, move, self_damage=self_damage, log=self.log)
    r_defence = self.defence_modifier(atk, move, self_damage=self_damage, log=self.log)
    r_damage = self.damage_modifier(atk, move, self_damage=self_damage, is_lethal=lethal_calc, log=self.log)
    # print(f"{move_type=}\n{r_attack_type=}\n{r_defence_type=}\n{r_power=}\n{r_attack=}\n{r_defence=}\n{r_damage=}")

    r_power *= power_multiplier

    # 最終威力
    final_power = max(1, ut.round_half_down(move.power*r_power/4096))

    # 最終攻撃・ランク補正
    if move.name == 'ボディプレス':
        stat_idx = 2
    elif move_category == MoveCategory.SPE:
        stat_idx = 3
    else:
        stat_idx = 1

    atk_idx2 = dfn if move.name == 'イカサマ' else atk

    final_attack = self.battle.pokemons[atk_idx2].stats[stat_idx]

    r_rank = self.battle.poke_mgrs[atk_idx2].rank_modifier(stat_idx)

    if defender_mgr.defending_ability(move).name == 'てんねん':
        if r_rank > 1:
            r_rank = 1
            self.log.notes.append('てんねん AC上昇無視')
    elif self.critical and r_rank < 1:
        r_rank = 1
        self.log.notes.append('急所 AC下降無視')

    final_attack = int(final_attack*r_rank)

    if attacker.ability.name == 'はりきり' and move_category == MoveCategory.PHY:
        final_attack = int(final_attack*1.5)
        self.log.notes.append('はりきり x1.5')

    final_attack = max(1, ut.round_half_down(final_attack*r_attack/4096))

    # 最終防御・ランク補正
    if move_category == MoveCategory.PHY or "physical" in move.tags:
        stat_idx = 2
    else:
        stat_idx = 4

    final_defence = defender.stats[stat_idx]

    if "ignore_rank" in move.tags:
        r_rank = 1
    else:
        r_rank = defender_mgr.rank_modifier(stat_idx)

    if defender_mgr.defending_ability(move).name == 'てんねん':
        if r_rank > 1:
            r_rank = 1
            self.log.notes.append('てんねん BD上昇無視')
    elif self.critical and r_rank > 1:
        r_rank = 1
        self.log.notes.append('急所 BD上昇無視')

    final_defence = int(final_defence*r_rank)

    # 雪・砂嵐補正
    if self.battle.field_mgr.weather() == Weather.SNOW and \
            'こおり' in defender_mgr.types and move_category == MoveCategory.PHY:
        final_defence = int(final_defence*1.5)
        self.log.notes.append('ゆき 防御 x1.5')
    elif self.battle.field_mgr.weather() == Weather.SAND and \
            'いわ' in defender_mgr.types and move_category == MoveCategory.SPE:
        final_defence = int(final_defence*1.5)
        self.log.notes.append('すなあらし 特防 x1.5')

    final_defence = max(1, ut.round_half_down(final_defence*r_defence/4096))

    # 最大乱数ダメージ
    max_damage = int(int(int(attacker.level*0.4+2)*final_power*final_attack/final_defence)/50+2)
    # print(f"{max_damage=}\n{attacker.level=}\n{final_power=}\n{final_attack=}\n{final_defence=}")

    # はれ・あめ補正
    if self.battle.field_mgr.weather(dfn) == Weather.SUNNY:
        match move_type:
            case 'ほのお':
                max_damage = ut.round_half_down(max_damage*1.5)
                self.log.notes.append('はれ x1.5')
            case 'みず':
                max_damage = ut.round_half_down(max_damage*0.5)
                self.log.notes.append('はれ x0.5')

    elif self.battle.field_mgr.weather(dfn) == Weather.RAINY:
        match move_type:
            case 'ほのお':
                max_damage = ut.round_half_down(max_damage*0.5)
                self.log.notes.append('あめ x0.5')
            case 'みず':
                max_damage = ut.round_half_down(max_damage*1.5)
                self.log.notes.append('あめ x1.5')

    # きょけんとつげき副作用
    if defender_mgr.executed_move.name == 'きょけんとつげき' and \
            dfn == self.battle.turn_mgr.first_player_idx:
        max_damage = ut.round_half_down(max_damage*2)
        self.log.notes.append('きょけんとつげき x2.0')

    # 急所
    if self.critical:
        max_damage = ut.round_half_down(max_damage*1.5)
        self.log.notes.append('急所 x1.5')

    damages = [0]*16

    for i in range(16):
        # 乱数 85~100%
        damages[i] = int(max_damage*(0.85+0.01*i))

        # 攻撃タイプ補正
        damages[i] = ut.round_half_down(damages[i]*r_attack_type)

        # 防御タイプ補正
        damages[i] = int(damages[i]*r_defence_type)

        # 状態異常補正
        if attacker.ailment == Ailment.BRN and move_category == MoveCategory.PHY and \
                attacker.ability.name != 'こんじょう' and move.name != 'からげんき':
            damages[i] = ut.round_half_down(damages[i]*0.5)
            if i == 0:
                self.log.notes.append('やけど x0.5')

        # ダメージ補正
        damages[i] = ut.round_half_down(damages[i] * r_damage / 4096)

        # 最低ダメージ補償
        if damages[i] == 0 and r_defence_type * r_damage > 0:
            damages[i] = 1

    return damages
