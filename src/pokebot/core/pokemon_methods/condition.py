from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..active_pokemon_manager import ActivePokemonManager

from pokebot.common.enums import Condition, SideField, Weather, Terrain
from pokebot.pokedb import Move
from pokebot.logger import TurnLog


def set_count(self: ActivePokemonManager, condition: Condition, count: int):
    self.count[condition] = count
    if condition in [Condition.CONFUSION]:
        count = ""
    self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{condition} {count}"))


def _set_condition(self: ActivePokemonManager,
                   condition: Condition,
                   count: int,
                   move: Move | None) -> bool:
    # 状態が変わらなければFalse
    if count == self.count[condition]:
        return False

    # 重ね掛け不可
    if condition not in [Condition.STOCK, Condition.CRITICAL] and \
            count and self.count[condition]:
        return False

    if move is None:
        ability = self.pokemon.ability
    else:
        ability = self.defending_ability(move)

    # 状態ごとの判定
    match condition:
        case Condition.ENCORE:
            if ability.name == 'アロマベール':
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{ability}により無効"))
                return False
            if not self.expended_moves or \
                    self.expended_moves[-1].pp == 0 or \
                    'non_encore' in self.expended_moves[-1].tags:
                return False

        case Condition.CHOHATSU:
            if ability.name in ['アロマベール', 'どんかん']:
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{ability}により無効"))
                return False

        case Condition.HEAL_BLOCK:
            if ability.name == 'アロマベール':
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{ability}により無効"))
                return False

        case Condition.KANASHIBARI:
            if ability.name == 'アロマベール':
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{ability}により無効"))
                return False
            if not self.executed_move or self.executed_move.name == 'わるあがき':
                return False

        case Condition.CONFUSION:
            if ability.name == 'マイペース':
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{ability}により無効"))
                return False

        case Condition.NEMUKE:
            if self.pokemon.ailment.value:
                return False
            if self.battle.field_mgr.count[SideField.SHINPI][self.idx]:
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{SideField.SHINPI}により無効"))
            if ability.name in ['ふみん', 'やるき', 'スイートベール', 'きよめのしお', 'ぜったいねむり', 'リミットシールド'] or \
                    (ability.name == 'リーフガード' and self.battle.field_mgr.weather(self.idx) == Weather.SUNNY) or \
                    (ability.name == 'フラワーベール' and 'くさ' in self.types):
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{ability}により無効"))
            if self.battle.field_mgr.terrain(self.idx) == Terrain.ELEC:
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{Terrain.ELEC}により無効"))
                return False

        case Condition.MEROMERO:
            if not self.pokemon.gender.value or \
                    not self.opponent.gender.value or \
                    self.pokemon.gender == self.opponent.gender:
                return False
            if ability.name in ['アロマベール', 'どんかん']:
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{ability}により無効"))
                return False

        case Condition.YADORIGI:
            if "くさ" in self.types:
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx, "タイプ無効"))
                return False

    set_count(self, condition, count)

    if condition == Condition.MEROMERO and self.pokemon.item.name == "あかいいと":
        self.battle.poke_mgrs[self.idx].activate_item()

    return True


def _add_condition_count(self: ActivePokemonManager,
                         condition: Condition,
                         v: int) -> bool:
    count = self.count[condition]

    if (v < 0 and count == 0) or (v > 0 and count == condition.max_count):
        return False

    set_count(self, condition, max(0, min(condition.max_count, count + v)))

    return True
