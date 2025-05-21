from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..pokemon_manager import ActivePokemonManager

from pokebot.common.enums import Condition
from pokebot.common.constants import HEAL_BERRIES
from pokebot.model import Move
from pokebot.logger import TurnLog


def _add_hp(self: ActivePokemonManager,
            value: int,
            move: Move | None) -> bool:
    """
    場のポケモンのHPに加算する

    Parameters
    ----------
    battle : Battle
        対象のバトル
    self.idx : int
        対象のプレイヤー番号
    value : int, optional
        加算するHP量, by default None
    move : Move, optional
        Noneでなければ技による変動とみなす, by default None

    Returns
    -------
    bool
        HPが変動したらTrue
    """
    # 回復
    if value > 0:
        if self.pokemon.hp_ratio == 1 or \
                (self.count[Condition.HEAL_BLOCK] and move and move.name != 'いたみわけ'):
            return False
        else:
            old_hp = self.pokemon.hp
            self.pokemon.hp = min(self.pokemon.stats[0], self.pokemon.hp + value)
            self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"HP +{self.pokemon.hp - old_hp}"))

    # ダメージ
    else:
        if self.pokemon.hp == 0 or (not move and self.pokemon.ability.name == 'マジックガード'):
            return False

        old_hp = self.pokemon.hp
        self.pokemon.hp = max(0, self.pokemon.hp + value)
        self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"HP {self.pokemon.hp - old_hp}"))

        # ぎゃくじょう判定
        if move and move.name != 'わるあがき' and \
                old_hp >= self.pokemon.stats[0]/2 and self.pokemon.hp_ratio <= 0.5:
            self.berserk_triggered = True

        # 回復実の判定
        if self.pokemon.hp and self.pokemon.item.name in HEAL_BERRIES and \
                move and move.name not in ['ついばむ', 'むしくい', 'やきつくす']:
            self.activate_item()

    return True
