from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import MoveCategory, Weather, Condition, GlobalField
import pokebot.common.utils as ut
from pokebot.pokedb import Move


def hit_probability(battle: Battle,
                    atk: PlayerIndex | int,
                    move: Move) -> float:

    dfn = int(not atk)
    attacker_mgr = battle.poke_mgrs[atk]
    defender_mgr = battle.poke_mgrs[dfn]
    attacker = attacker_mgr.pokemon
    defender = defender_mgr.pokemon

    defender_ability = battle.poke_mgrs[dfn].defending_ability(move)

    # 必中判定
    if attacker_mgr.lockon or \
        'ノーガード' in attacker.ability.name + defender_ability.name or \
        (battle.field_mgr.weather(dfn) == Weather.RAINY and "rainy_hit" in move.tags) or \
            (battle.field_mgr.weather() == Weather.SNOW and move.name == 'ふぶき') or \
            (move.name == 'どくどく' and 'どく' in attacker_mgr.types):
        return 1

    # 隠れる技
    if defender_mgr.hidden and defender_mgr.executed_move:
        match defender_mgr.executed_move.name:
            case 'あなをほる':
                if move.name not in ['じしん', 'マグニチュード']:
                    return 0
            case 'そらをとぶ' | 'とびはねる':
                if move.name not in ['かぜおこし', 'かみなり', 'たつまき', 'スカイアッパー',
                                     'うちおとす', 'ぼうふう', 'サウザンアロー']:
                    return 0
            case 'ダイビング':
                if move.name not in ['なみのり', 'うずしお']:
                    return 0

    # ぜったいれいど
    if "one_ko" in move.tags:
        if move.name == 'ぜったいれいど' and 'こおり' not in attacker_mgr.types:
            return 0.2
        else:
            return 0.3

    # 技の命中率
    prob = move.hit

    if battle.field_mgr.weather(atk) == Weather.SUNNY and move.name in ['かみなり', 'ぼうふう']:
        prob *= 0.5
    if defender_ability.name == 'ミラクルスキン' and move.category == MoveCategory.STA and move.hit <= 100:
        prob = min(prob, 50)

    # 命中補正
    m = 4096

    if battle.field_mgr.count[GlobalField.GRAVITY]:
        m = ut.round_half_up(m*6840/4096)

    match attacker.ability.name:
        case 'はりきり':
            if move.category == MoveCategory.PHY:
                m = ut.round_half_up(m*3277/4096)
        case 'ふくがん':
            m = ut.round_half_up(m*5325/4096)
        case 'しょうりのほし':
            m = ut.round_half_up(m*4506/4096)

    match defender_ability.name:
        case 'ちどりあし':
            if defender_mgr.count[Condition.CONFUSION]:
                m = ut.round_half_up(m*0.5)
        case 'すながくれ':
            if battle.field_mgr.weather() == Weather.SAND:
                m = ut.round_half_up(m*3277/4096)
        case 'ゆきがくれ':
            if battle.field_mgr.weather() == Weather.SNOW:
                m = ut.round_half_up(m*3277/4096)

    match attacker.item.name:
        case 'こうかくレンズ':
            m = ut.round_half_up(m*4505/4096)
        case 'フォーカスレンズ':
            if atk != battle.turn_mgr.first_player_idx:
                m = ut.round_half_up(m*4915/4096)

    if defender.item.name in ['のんきのおこう', 'ひかりのこな']:
        m = ut.round_half_up(m*3686/4096)

    # ランク補正
    delta = attacker_mgr.rank[6]*(defender_ability.name != 'てんねん')
    if attacker.ability.name not in ['しんがん', 'てんねん', 'するどいめ', 'はっこう'] and \
            "ignore_rank" not in move.tags:
        delta -= defender_mgr.rank[7]
    delta = max(-6, min(6, delta))
    r = (3+delta)/3 if delta >= 0 else 3/(3-delta)

    return int(ut.round_half_down(prob*m/4096)*r)/100
