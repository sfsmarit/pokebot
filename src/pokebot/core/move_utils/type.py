from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import MoveCategory
from pokebot.common.constants import WEATHER_BALL_TYPE
from pokebot.pokedb import Move


def effective_move_type(battle: Battle,
                        atk: PlayerIndex | int,
                        move: Move | str) -> str:
    """発動した技の実効的なタイプ"""
    if isinstance(move, str):
        move = Move(move)

    attacker_mgr = battle.poke_mgrs[atk]
    attacker = attacker_mgr.pokemon

    if move.name in ['テラバースト', 'テラクラスター'] and attacker.terastal:
        return attacker.terastal

    match attacker.ability.name:
        case 'うるおいボイス':
            if "sound" in move.tags:
                return 'みず'
        case 'エレキスキン':
            if move.type == 'ノーマル':
                return 'でんき'
        case 'スカイスキン':
            if move.type == 'ノーマル':
                return 'ひこう'
        case 'ノーマルスキン':
            return 'ノーマル'
        case 'フェアリースキン':
            if move.type == 'ノーマル':
                return 'フェアリー'
        case 'フリーズスキン':
            if move.type == 'ノーマル':
                return 'こおり'

    match move.name:
        case 'ウェザーボール':
            return WEATHER_BALL_TYPE[battle.field_mgr.weather(atk)]
        case 'さばきのつぶて' | 'めざめるダンス':
            return attacker_mgr.types[0]
        case 'ツタこんぼう':
            if 'オーガポン(' in attacker.name:
                return attacker._types[-1]
        case 'レイジングブル':
            return attacker_mgr.types[-1]

    return move.type


def effective_move_category(battle: Battle,
                            atk: PlayerIndex | int,
                            move: Move | str) -> MoveCategory:
    if isinstance(move, str):
        move = Move(move)

    attacker_mgr = battle.poke_mgrs[atk]
    attacker = attacker_mgr.pokemon

    if move.name in ['テラバースト', 'テラクラスター'] and attacker.terastal:
        effA = attacker._stats[1] * attacker_mgr.rank_modifier(1)
        effC = attacker._stats[3] * attacker_mgr.rank_modifier(3)
        if effA >= effC:
            return MoveCategory.PHY
        else:
            return MoveCategory.SPE
    else:
        return move.category
