from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..active_pokemon_manager import ActivePokemonManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import SideField, Weather
from pokebot.model import Pokemon
from pokebot.logger import TurnLog


def _add_rank(self: ActivePokemonManager,
              values: list[int],
              by_opponent: bool,
              chain: bool) -> list[int]:

    opp = int(not self.idx)
    opponent_mgr = self.battle.poke_mgrs[opp]

    delta = [0]*8
    reflection = [0]*8

    for i, v in enumerate(values):
        if i == 0 or v == 0:
            continue

        if self.pokemon.item.name == 'クリアチャーム' and by_opponent and v < 0:
            self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{self.pokemon.item}により無効"))
            continue

        if self.pokemon.ability.name == 'あまのじゃく':
            v *= -1

        if self.rank[i] * v / abs(v) == 6:
            continue

        if v < 0 and by_opponent:
            if self.battle.field_mgr.count[SideField.WHITE_MIST][self.idx]:
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{SideField.WHITE_MIST}により無効"))
                continue

            match self.pokemon.ability.name:
                case 'クリアボディ' | 'しろいけむり' | 'メタルプロテクト':
                    self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{self.pokemon.ability}により無効"))
                    continue
                case 'フラワーベール':
                    if "くさ" in self.types:
                        self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{self.pokemon.ability}により無効"))
                        continue
                case 'かいりきバサミ':
                    if i == 1:
                        self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{self.pokemon.ability}により無効"))
                        continue
                case 'はとむね':
                    if i == 2:
                        self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{self.pokemon.ability}により無効"))
                        continue
                case 'しんがん' | 'するどいめ':
                    if i == 6:
                        self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{self.pokemon.ability}により無効"))
                        continue
                case 'ミラーアーマー':
                    reflection[i] = v
                    continue

        prev = self.rank[i]
        self.rank[i] = max(-6, min(6, prev + v * (2 if self.pokemon.ability.name == 'たんじゅん' else 1)))
        delta[i] = self.rank[i] - prev

    if any(reflection) and not chain and opponent_mgr.add_rank(values=reflection, chain=True):
        self.battle.logger.append(TurnLog(self.battle.turn, self.idx, self.pokemon.ability.name))

    if not any(delta):
        return []

    self.rank_dropped = any(v < 0 for v in delta)

    self.battle.logger.append(TurnLog(self.battle.turn, self.idx, Pokemon.rank2str(delta)))

    if by_opponent and any([min(0, v) for v in delta]):
        match self.pokemon.ability.name:
            case 'かちき':
                if self.add_rank(3, +2):
                    self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, self.pokemon.ability.name))
            case 'まけんき':
                if self.add_rank(1, +2):
                    self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, self.pokemon.ability.name))

    if any(pos_delta := [max(0, v) for v in delta]) and not chain:
        if self.opponent.ability.name == 'びんじょう' and opponent_mgr.add_rank(values=pos_delta, chain=True):
            self.battle.logger.insert(-1, TurnLog(self.battle.turn, opp, self.opponent.ability.name))
        if self.opponent.item.name == 'ものまねハーブ' and opponent_mgr.add_rank(values=pos_delta, chain=True):
            self.battle.poke_mgrs[opp].activate_item()

    return delta
