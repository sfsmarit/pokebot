from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .battle import Battle

from pokebot.common.types import PlayerIndex
import pokebot.common.utils as ut
from pokebot.model import Move
from pokebot.logger.damage_log import DamageLog

from .damage_methods.single_hit_damages import _single_hit_damages
from .damage_methods.lethal import lethal
from .damage_methods.attack_type_modifier import _attack_type_modifier
from .damage_methods.defence_type_modifier import _defence_type_modifier
from .damage_methods.power_modifier import _power_modifier
from .damage_methods.attack_modifier import _attack_modifier
from .damage_methods.defence_modifier import _defence_modifier
from .damage_methods.damage_modifier import _damage_modifier


class DamageManager:
    def __init__(self, battle: Battle):
        self.battle: Battle = battle

        self.log: DamageLog
        self.critical: bool = False

        self.lethal_num: int
        self.lethal_prob: float
        self.hp_dstr: dict = {}
        self.damage_dstr: dict = {}
        self.damage_ratio_dstr: dict = {}

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new, keys_to_deepcopy=["log"])
        return new

    def single_hit_damages(self,
                           atk: PlayerIndex | int,
                           move: Move | str,
                           critical: bool = False,
                           power_multiplier: float = 1,
                           self_damage: bool = False,
                           lethal_calc: bool = False) -> list[int]:
        if isinstance(move, str):
            move = Move(move)
        self.critical = critical
        self.log = DamageLog(self.battle, atk, move)
        return _single_hit_damages(self, atk, move, power_multiplier, self_damage, lethal_calc)

    def lethal(self,
               atk: PlayerIndex | int,
               move_list: list[Move | str],
               combo_hits: int | None = None,
               max_loop: int = 10) -> str:
        """
        致死率計算

        Parameters
        ----------
        battle: Battle
            Battleインスタンス
        atk: PlayerIndex | int
            攻撃側のプレイヤー番号
        move_list: [str]
            攻撃技. 2個以上の場合は加算ダメージを計算
        combo_hits: int
            連続技の回数
        max_loop: int
            計算ループの上限回数

        Returns
        ----------
        str
            "d1~d2 (p1~p2 %) 確n" 形式の文字列.
        """
        lethal(self, atk, move_list, combo_hits, max_loop)
        return self.lethal_text()

    def lethal_text(self) -> str:
        """致死率計算の結果から 'd1~d2 (r1~r2 %) 乱n (p%)' の文字列を生成"""
        damages = [int(k) for k in list(self.damage_dstr.keys())]
        damage_ratios = [float(k) for k in list(self.damage_ratio_dstr.keys())]
        text = f"{min(damages)}~{max(damages)} ({100*min(damage_ratios):.1f}~{100*max(damage_ratios):.1f}%)"
        if self.lethal_prob == 1:
            text += f" 確{self.lethal_num}"
        elif self.lethal_prob > 0:
            text += f" 乱{self.lethal_num}({100*self.lethal_prob:.2f}%)"
        return text

    def attack_type_modifier(self,
                             atk: PlayerIndex | int,
                             move: Move,
                             log: DamageLog | None = None) -> float:
        return _attack_type_modifier(self, atk, move, log)

    def defence_type_modifier(self,
                              atk: PlayerIndex | int,
                              move: Move,
                              self_damage: bool = False,
                              log: DamageLog | None = None) -> float:
        return _defence_type_modifier(self, atk, move, self_damage, log)

    def power_modifier(self,
                       atk: PlayerIndex | int,
                       move: Move,
                       self_damage: bool = False,
                       log: DamageLog | None = None) -> float:
        return _power_modifier(self, atk, move, self_damage, log)

    def attack_modifier(self,
                        atk: PlayerIndex | int,
                        move: Move,
                        self_damage: bool = False,
                        log: DamageLog | None = None) -> float:
        return _attack_modifier(self, atk, move, self_damage, log)

    def defence_modifier(self,
                         atk: PlayerIndex | int,
                         move: Move,
                         self_damage: bool = False,
                         log: DamageLog | None = None) -> float:
        return _defence_modifier(self, atk, move, self_damage, log)

    def damage_modifier(self,
                        atk: PlayerIndex | int,
                        move: Move,
                        self_damage: bool = False,
                        is_lethal: bool = False,
                        log: DamageLog | None = None):
        return _damage_modifier(self, atk, move, self_damage, is_lethal, log)
