from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import MoveCategory, Terrain
# from pokebot.common import PokeDB
from pokebot.pokedb import Move
from pokebot.logger import TurnLog


def move_speed(battle: Battle,
               atk: PlayerIndex | int,
               move: Move) -> float:
    """技による行動速度. 上位優先度(1e0)+下位優先度(1e-1)"""
    attacker = battle.pokemons[atk]

    speed = move.priority

    # 上位優先度 (1e0)
    match attacker.ability.name:
        case 'いたずらごころ':
            if move.category == MoveCategory.STA:
                speed += 1
                battle.logger.append(TurnLog(battle.turn, atk, attacker.ability.name))
        case 'はやてのつばさ':
            if attacker.hp_ratio == 1 and move.type == 'ひこう':
                speed += 1
                battle.logger.append(TurnLog(battle.turn, atk, attacker.ability.name))
        case 'ヒーリングシフト':
            if "heal" in move.tags or PokeDB.get_move_effect_value(move, "drain"):
                speed += 3
                battle.logger.append(TurnLog(battle.turn, atk, attacker.ability.name))

    if move.name == 'グラススライダー' and battle.field_mgr.terrain(atk) == Terrain.GRASS:
        speed += 1

    # 下位優先度 (1e-1)
    if attacker.ability.name == 'きんしのちから' and move.category == MoveCategory.STA:
        speed -= 1e-1
        battle.logger.append(TurnLog(battle.turn, atk, attacker.ability.name))
    elif attacker.ability.name == 'クイックドロウ' and (battle.is_test or battle.random.random() < 0.3):
        speed += 1e-1
        battle.logger.append(TurnLog(battle.turn, atk, attacker.ability.name))
    elif attacker.item.name == 'せんせいのツメ' and battle.poke_mgrs[atk].activate_item:
        speed += 1e-1
    elif attacker.item.name == 'イバンのみ' and battle.poke_mgrs[atk].activate_item:
        speed += 1e-1
    else:
        if attacker.ability.name == 'あとだし':
            speed -= 1e-1
            battle.logger.append(TurnLog(battle.turn, atk, attacker.ability.name))
        if attacker.item.name in ['こうこうのしっぽ', 'まんぷくおこう']:
            speed -= 1e-1

    return speed
