from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..pokemon_manager import ActivePokemonManager

from pokebot.common.enums import MoveCategory, Condition
from pokebot.common import PokeDB
from pokebot.model import Move


def _can_choose_move(self: ActivePokemonManager,
                     move: Move) -> list[bool | str]:
    """[技を選択できればTrue, 選択できない理由] を返す"""

    if move.name == "わるあがき":
        return [True, ""]

    if move.pp == 0:
        return [False, 'PP切れ']

    if self.count[Condition.ENCORE] and \
            self.expended_moves and \
            move.name != self.expended_moves[-1].name:
        return [False, 'アンコール状態']

    if self.count[Condition.HEAL_BLOCK] and \
            ("heal" in move.tags or PokeDB.get_move_effect_value(move, 'drain')):
        return [False, 'かいふくふうじ状態']

    if self.count[Condition.KANASHIBARI] and \
            self.expended_moves and \
            move.name == self.expended_moves[-1].name:
        return [False, 'かなしばり状態']

    if self.count[Condition.JIGOKUZUKI] and \
            "sound" in move.tags:
        return [False, 'じごくづき状態']

    if self.count[Condition.CHOHATSU] and \
            move.category == MoveCategory.STA:
        return [False, 'ちょうはつ状態']

    if any(tag in move.tags for tag in ["unrepeatable", "protect"]) and \
            self.executed_move and \
            move.name == self.executed_move.name:
        return [False, '連発不可']

    if self.choice_locked and \
            self.expended_moves and \
            move.name != self.expended_moves[-1].name:
        return [False, 'こだわり状態']

    if self.pokemon.item.name == 'とつげきチョッキ' and \
            move.category == MoveCategory.STA:
        return [False, 'とつげきチョッキ']

    return [True, ""]
