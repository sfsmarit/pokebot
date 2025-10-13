from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.pokemon import Pokemon
    from pokebot.core.move import Move

from dataclasses import dataclass

from .events import EventManager, Event, EventContext
import pokebot.common.utils as ut
from pokebot.common.enums import MoveCategory, Stat
from pokebot.core.pokedb import PokeDB


@dataclass
class DamageContext:
    critical: bool = False
    self_harm: bool = False
    power_multiplier: float = 1
    is_lethal_calc: bool = False


def rank_modifier(v: float) -> float:
    return (2+v)/2 if v >= 0 else 2/(2-v)


class DamageCalculator:
    def __init__(self, events: EventManager):
        self.events: EventManager = events

        self.logs: list[str] = []

        self.lethal_num: int = 0
        self.lethal_prob: float = 0.
        self.hp_dstr: dict = {}
        self.damage_dstr: dict = {}
        self.damage_ratio_dstr: dict = {}

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        # ut.selective_deepcopy(self, new, keys_to_deepcopy=["log"])
        return new

    def single_hit_damages(self,
                           attacker: Pokemon,
                           defender: Pokemon,
                           move: Move,
                           dctx: DamageContext | None = None) -> list[int]:
        # ダメージを与えない技なら中断
        if not move.data.power:
            return [0]

        if dctx is None:
            dctx = DamageContext()

        move_category = attacker.effective_move_category(move, self.events)

        # ---------------- 最終威力 ----------------
        # 技威力
        final_pow = move.data.power * dctx.power_multiplier

        # その他の補正
        r_pow = self.events.emit(Event.ON_CALC_POWER_MODIFIER,
                                 EventContext(attacker, move, value=4096))
        final_pow = ut.round_half_down(final_pow * r_pow/4096)
        final_pow = max(1, final_pow)

        # ---------------- 最終攻撃 ----------------
        # ステータス
        if move == 'イカサマ':
            final_atk = defender.stats[Stat.A.idx]
            r_rank = rank_modifier(defender.field_status.rank[Stat.A.idx])
        else:
            if move == 'ボディプレス':
                stat = Stat.B
            elif move_category == MoveCategory.PHY:
                stat = Stat.A
            else:
                stat = Stat.C
            final_atk = attacker.stats[stat.idx]
            r_rank = rank_modifier(attacker.field_status.rank[stat.idx])

        # ランク補正の修正
        def_ability = self.events.emit(Event.ON_CHECK_DEF_ABILITY,
                                       ctx=EventContext(defender, move, defender.ability))

        if def_ability == 'てんねん' and r_rank != 1:
            r_rank = 1
            self.logs.append(f"{def_ability}")

        if dctx.critical and r_rank < 1:
            r_rank = 1
            self.logs.append('急所 AC下降無視')

        if r_rank != 1:
            self.logs.append(f"攻撃ランク x{r_rank:.1f}")

        # ランク補正
        final_atk = int(final_atk * r_rank)

        # その他の補正
        r_atk = self.events.emit(Event.ON_CALC_ATK_MODIFIER,
                                 EventContext(attacker, move, value=4096))
        final_atk = ut.round_half_down(final_atk * r_atk/4096)
        final_atk = max(1, final_atk)

        # ---------------- 最終防御 ----------------
        # ステータス
        if move_category == MoveCategory.PHY or "physical" in move.data.flags:
            stat = Stat.B
        else:
            stat = Stat.D

        final_def = defender.stats[stat.idx]
        r_rank = rank_modifier(defender.field_status.rank[stat.idx])

        # ランク補正の修正
        if "ignore_rank" in move.data.flags and r_rank != 1:
            r_rank = 1
            self.logs.append(f"{move} 防御ランク無視")

        if attacker.ability == 'てんねん' and r_rank != 1:
            r_rank = 1
            self.logs.append(f"{def_ability}")

        if dctx.critical and r_rank > 1:
            r_rank = 1
            self.logs.append('急所 BD上昇無視')

        if r_rank != 1:
            self.logs.append(f"防御ランク x{r_rank:.1f}")

        # ランク補正
        final_def = int(final_def * r_rank)

        # その他の補正
        r_def = self.events.emit(Event.ON_CALC_DEF_MODIFIER,
                                 EventContext(defender, move, value=4096))
        final_def = ut.round_half_down(final_def * r_def/4096)
        final_def = max(1, final_def)

        # ---------------- ダメージ計算 ----------------
        # 最大乱数ダメージ
        max_damage = int(int(int(attacker.level*0.4+2)*final_pow*final_atk/final_def)/50+2)

        # 急所
        if dctx.critical:
            max_damage = ut.round_half_down(max_damage * 1.5)
            self.logs.append("急所 x1.5")

        # その他の補正
        r_atk_type = self.events.emit(Event.ON_CALC_ATK_TYPE_MODIFIER,
                                      EventContext(defender, move, value=4096))
        r_def_type = self.events.emit(Event.ON_CALC_DEF_TYPE_MODIFIER,
                                      EventContext(defender, move, value=1))
        r_damage = self.events.emit(Event.ON_CALC_DAMAGE_MODIFIER,
                                    EventContext(defender, move, value=1))

        damages = [0]*16

        for i in range(16):
            # 乱数 85~100%
            damages[i] = int(max_damage * (0.85+0.01*i))

            # 補正
            damages[i] = ut.round_half_down(damages[i] * r_atk_type)
            damages[i] = int(damages[i] * r_def_type)
            damages[i] = ut.round_half_down(damages[i] * r_damage/4096)

            # 最低ダメージ補償
            if damages[i] == 0 and r_def_type * r_damage > 0:
                damages[i] = 1

        print(f"{final_pow=} {final_atk=} {final_def=}")
        print(f"{damages=}")

        return damages
