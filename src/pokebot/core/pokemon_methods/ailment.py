from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..pokemon_manager import ActivePokemonManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Ailment, MoveCategory, Condition, \
    SideField, Weather, Terrain
from pokebot.model import Move
from pokebot.logger import TurnLog


def _set_ailment(self: ActivePokemonManager,
                 ailment: Ailment,
                 move: Move,
                 bad_poison: bool,
                 ignore_shinpi: bool) -> bool:

    battle = self.battle
    opp = int(not self.idx)

    if self.pokemon.ailment == ailment:
        return False

    ability = self.defending_ability(move)

    # 状態異常の解除
    if not ailment.value:
        self.pokemon.ailment = Ailment.NONE
        self.pokemon.sleep_count = 0
        battle.logger.append(TurnLog(battle.turn, self.idx, "状態異常解除"))
        return True

    if move.name != 'ねむる':
        # 状態異常の上書き不可
        if self.pokemon.ailment != Ailment.NONE:
            return False
        # しんぴのまもり
        if battle.field_mgr.count[SideField.SHINPI][self.idx] and not ignore_shinpi:
            return False

    # すべての状態異常を無効にする条件
    if ability.name in ['きよめのしお', 'ぜったいねむり'] or \
        (ability.name == 'リーフガード' and battle.field_mgr.weather(self.idx) == Weather.SUNNY) or \
            (ability.name == 'フラワーベール' and 'くさ' in self.types):
        battle.logger.append(TurnLog(battle.turn, self.idx, ability.name))
        return False

    # ミストフィールドによる無効
    if battle.field_mgr.terrain(self.idx) == Terrain.MIST:
        battle.logger.append(TurnLog(battle.turn, self.idx, str(Terrain.MIST)))
        return False

    # 特定の状態異常を無効にする条件
    match ailment:
        case Ailment.PSN:
            if ability.name in ['めんえき', 'パステルベール']:
                battle.logger.append(TurnLog(battle.turn, self.idx, ability.name))
                return False
            if any(t in self.types for t in ['どく', 'はがね']) and \
                    not (self.opponent.ability.name == 'ふしょく' and move.category == MoveCategory.STA):
                return False
        case Ailment.PAR:
            if 'でんき' in self.types:
                return False
            if ability.name == 'じゅうなん':
                battle.logger.append(TurnLog(battle.turn, self.idx, ability.name))
                return False
            if move.name == 'でんじは' and 'じめん' in self.types:
                return False
        case Ailment.BRN:
            if 'ほのお' in self.types:
                return False
            if ability in ['すいほう', 'ねつこうかん', 'みずのベール']:
                battle.logger.append(TurnLog(battle.turn, self.idx, ability.name))
                return False
        case Ailment.SLP:
            if ability in ['スイートベール', 'やるき', 'ふみん']:
                battle.logger.append(TurnLog(battle.turn, self.idx, ability.name))
                return False
            if battle.field_mgr.terrain(self.idx) == Terrain.ELEC:
                return False
        case Ailment.FLZ:
            if 'こおり' in self.types:
                return False
            if ability.name == 'マグマのよろい':
                battle.logger.append(TurnLog(battle.turn, self.idx, ability.name))
                return False
            if battle.field_mgr.weather(self.idx) == Weather.SUNNY:
                return False

    self.pokemon.ailment = ailment
    battle.logger.append(TurnLog(battle.turn, self.idx, str(self.pokemon.ailment)))

    match self.pokemon.ailment:
        case Ailment.PSN:
            # もうどく設定
            self.set_condition(Condition.BAD_POISON, int(bad_poison))
            if self.opponent.ability.name == 'どくくぐつ' and \
                    self.set_condition(Condition.CONFUSION, battle.random.randint(2, 5)):
                battle.logger.insert(-1, TurnLog(battle.turn, self.idx, self.opponent.ability.name))
        case Ailment.SLP:
            # ねむりターン設定
            if move.name == 'ねむる':
                self.pokemon.sleep_count = 3
            else:
                battle.random.randint(2, 4)
            self.set_condition(Condition.NEMUKE, 0)
            self.forced_turn = 0

    if self.pokemon.ability.name == 'シンクロ' and \
            move.name != 'ねむる' and \
            battle.poke_mgrs[opp].set_ailment(ailment):
        battle.logger.insert(-1, TurnLog(battle.turn, self.idx, self.pokemon.ability.name))

    return True
