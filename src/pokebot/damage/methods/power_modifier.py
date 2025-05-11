from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..damage_manager import DamageManager

from pokebot.common.enums import Ailment, MoveCategory, \
    Weather, Terrain, GlobalField
from pokebot.common.types import PlayerIndex
import pokebot.common.utils as ut
from pokebot.core import Move
from pokebot.core import PokeDB
from pokebot.logger.damage_log import DamageLog

from pokebot.move import effective_move_category, effective_move_type


def _power_modifier(self: DamageManager,
                    atk: PlayerIndex,
                    move: Move,
                    self_damage: bool,
                    log: DamageLog | None) -> float:

    dfn = atk if self_damage else PlayerIndex(not atk)
    attacker_mgr = self.battle.poke_mgr[atk]
    defender_mgr = self.battle.poke_mgr[dfn]
    attacker = attacker_mgr.pokemon
    defender = defender_mgr.pokemon

    move_type = effective_move_type(self.battle, atk, move)
    move_category = effective_move_category(self.battle, atk, move)

    r = 4096

    # 攻撃側
    if 'オーガポン(' in attacker.name:
        r = ut.round_half_up(r*4915/4096)
        if log:
            log.notes.append('おめん x1.2')

    # 威力変動技
    r0 = r
    match move.name:
        case 'アクロバット':
            if attacker.item.name:
                r = ut.round_half_up(r*2)
        case 'アシストパワー' | 'つけあがる':
            r = ut.round_half_up(
                r*(1 + sum(v for v in attacker_mgr.rank[1:] if v >= 0)))
        case 'ウェザーボール':
            if self.battle.field_mgr.weather(atk):
                r = ut.round_half_up(r*2)
        case 'エレキボール':
            x = attacker_mgr.effective_speed() / defender_mgr.effective_speed()
            if x >= 4:
                r *= 150
            elif x >= 3:
                r *= 120
            elif x >= 2:
                r *= 80
            elif x >= 1:
                r *= 60
            else:
                r *= 40
        case 'おはかまいり':
            r *= (1 + sum(1 for p in self.battle.selected_pokemons(atk) if p.hp == 0))
        case 'からげんき':
            if attacker.ailment:
                r = ut.round_half_up(r*2)
        case 'きしかいせい' | 'じたばた':
            x = int(48*attacker.hp_ratio)
            if x <= 1:
                r *= 200
            elif x <= 4:
                r *= 150
            elif x <= 9:
                r *= 100
            elif x <= 16:
                r *= 80
            elif x <= 32:
                r *= 40
            else:
                r *= 20
        case 'くさむすび' | 'けたぐり':
            weight = defender.weight
            if weight < 10:
                r *= 20
            elif weight < 25:
                r *= 40
            elif weight < 50:
                r *= 60
            elif weight < 100:
                r *= 80
            elif weight < 200:
                r *= 100
            else:
                r *= 120
        case 'しおふき' | 'ドラゴンエナジー' | 'ふんか':
            r = int(r*attacker.hp_ratio)
        case 'しおみず':
            if defender.hp_ratio <= 0.5:
                r = ut.round_half_up(r*2)
        case 'じだんだ' | 'やけっぱち':
            pass
        case 'しっぺがえし':
            if atk != self.battle.turn_mgr.first_player_idx:
                r = ut.round_half_up(r*2)
        case 'ジャイロボール':
            x = defender_mgr.effective_speed() / attacker_mgr.effective_speed()
            r = ut.round_half_up(r*min(150, int(1+25*x)))
        case 'Gのちから':
            if self.battle.field_mgr.count[GlobalField.GRAVITY]:
                r = ut.round_half_up(r*1.5)
        case 'たたりめ' | 'ひゃっきやこう':
            if defender.ailment:
                r = ut.round_half_up(r*2)
        case 'テラバースト':
            if attacker.terastal == 'ステラ' and attacker.terastal:
                r = ut.round_half_up(r*1.25)
        case 'なげつける':
            r = r * attacker.item.throw_power
        case 'にぎりつぶす' | 'ハードプレス':
            p0 = 120 if move.name == 'にぎりつぶす' else 100
            r *= ut.round_half_down(p0 * defender.hp_ratio)
        case 'はたきおとす':
            if not defender.item.name:
                r = ut.round_half_up(r*1.5)
        case 'ふんどのこぶし':
            r *= (1 + attacker_mgr.hits_taken)
        case 'ベノムショック':
            if defender.ailment == Ailment.PSN:
                r = ut.round_half_up(r*2)
        case 'ヒートスタンプ' | 'ヘビーボンバー':
            weight1, weight2 = attacker.weight, defender.weight
            if 2*weight2 > weight1:
                r *= 40
            elif 3*weight2 > weight1:
                r *= 60
            elif 4*weight2 > weight1:
                r *= 80
            elif 5*weight2 > weight1:
                r *= 100
            else:
                r *= 120
        case 'ゆきなだれ' | 'リベンジ':
            if atk != self.battle.turn_mgr.first_player_idx and \
                    self.battle.turn_mgr.damage_dealt[dfn]:
                r = ut.round_half_up(r*2)

    if r0 != r and log:
        log.notes.append(f"{move} x{r/r0:.1f}")

    if attacker.ability.name == 'テクニシャン' and move.power*r/4096 <= 60:
        r = ut.round_half_up(r*1.5)
        if log:
            log.notes.append(f"{attacker.ability} x1.5")

    # 以降の技はテクニシャン非適用
    if move.name in ['ソーラービーム', 'ソーラーブレード']:
        rate = 0.5 if self.battle.field_mgr.weather() == Weather.SAND else 1
        r = ut.round_half_up(r*rate)
        if rate != 1 and log:
            log.notes.append(f"{move} x{rate}")

    r0 = r
    match attacker.ability.name:
        case 'アナライズ':
            if atk != self.battle.turn_mgr.first_player_idx:
                r = ut.round_half_up(r*5325/4096)
        case 'エレキスキン':
            if move.type == 'ノーマル':
                r = ut.round_half_up(r*4915/4096)
        case 'かたいつめ':
            if "contact" in move.tags:
                r = ut.round_half_up(r*5325/4096)
        case 'がんじょうあご':
            if "bite" in move.tags:
                r = ut.round_half_up(r*1.5)
        case 'きれあじ':
            if "slash" in move.tags:
                r = ut.round_half_up(r*1.5)
        case 'スカイスキン':
            if move.type == 'ノーマル':
                r = ut.round_half_up(r*4915/4096)
        case 'すてみ':
            if PokeDB.get_move_effect_value(move, "recoil") or \
                    PokeDB.get_move_effect_value(move, "mis_recoil"):
                r = ut.round_half_up(r*4915/4096)
        case 'すなのちから':
            if self.battle.field_mgr.weather() == Weather.SAND and \
                    move_type in ['いわ', 'じめん', 'はがね']:
                r = ut.round_half_up(r*5325/4096)
        case 'そうだいしょう':
            vals = [4096, 4506, 4915, 5325, 5734, 6144]
            n = sum(p.hp == 0 for p in self.battle.selected_pokemons(atk))
            r = ut.round_half_up(r*vals[n]/4096)
        case 'ダークオーラ' | 'フェアリーオーラ':
            if (attacker.ability.name == 'ダークオーラ' and move_type == 'あく') or \
                    (attacker.ability.name == 'フェアリーオーラ' and move_type == 'フェアリー'):
                v = 5448/4096
                if defender.ability.name == 'オーラブレイク':
                    v = 1/v
                r = ut.round_half_up(r*v)
        case 'ちからずく':
            if move.name in PokeDB.move_effect:
                r = ut.round_half_up(r*5325/4096)
        case 'てつのこぶし':
            if "punch" in move.tags:
                r = ut.round_half_up(r*4915/4096)
        case 'とうそうしん':
            if attacker.gender.value and defender.gender.value:
                if attacker.gender == defender.gender:
                    r = ut.round_half_up(r*1.25)
                else:
                    r = ut.round_half_up(r*5072/4096)
        case 'どくぼうそう':
            if attacker.ailment == Ailment.PSN and move_category == MoveCategory.PHY:
                r = ut.round_half_up(r*1.5)
        case 'ノーマルスキン':
            if move.name != 'わるあがき' and move.type != 'ノーマル':
                r = ut.round_half_up(r*4915/4096)
        case 'パンクロック':
            if "sound" in move.tags:
                r = ut.round_half_up(r*5325/4096)
        case 'フェアリースキン':
            if move.type == 'ノーマル':
                r = ut.round_half_up(r*4915/4096)
        case 'フリーズスキン':
            if move.type == 'ノーマル':
                r = ut.round_half_up(r*4915/4096)
        case 'メガランチャー':
            if "wave" in move.tags:
                r = ut.round_half_up(r*1.5)

    if r != r0 and log:
        log.notes.append(f"{attacker.ability} x{r/r0:.1f}")

    r0 = r
    match attacker.item.name:
        case 'しらたま' | 'だいしらたま':
            if 'パルキア' in attacker.name and move_type in ['みず', 'ドラゴン']:
                r = ut.round_half_up(r*4915/4096)
        case 'こころのしずく':
            if attacker.name in ['ラティオス', 'ラティアス'] and move_type in ['エスパー', 'ドラゴン']:
                r = ut.round_half_up(r*4915/4096)
        case 'こんごうだま' | 'だいこんごうだま':
            if 'ディアルガ' in attacker.name and move_type in ['はがね', 'ドラゴン']:
                r = ut.round_half_up(r*4915/4096)
        case 'はっきんだま' | 'だいはっきんだま':
            if 'ギラティナ' in attacker.name and move_type in ['ゴースト', 'ドラゴン']:
                r = ut.round_half_up(r*4915/4096)
        case 'ちからのハチマキ':
            if move_category == MoveCategory.PHY:
                r = ut.round_half_up(r*4505/4096)
        case 'ノーマルジュエル':
            if move_type == 'ノーマル':
                r = ut.round_half_up(r*5325/4096)
                if log:
                    log.item_consumed[atk] = True
        case 'パンチグローブ':
            if "punch" in move.tags:
                r = ut.round_half_up(r*4506/4096)
        case 'ものしりメガネ':
            if move_category == MoveCategory.SPE:
                r = ut.round_half_up(r*4505/4096)
        case _:
            if move_type == attacker.item.buff_type:
                r = ut.round_half_up(r*4915/4096)

    if r != r0 and log:
        log.notes.append(f"{attacker.item} x{r/r0:.1f}")

    # 攻撃側のフィールド補正
    r0 = r
    match self.battle.field_mgr.terrain(atk):
        case Terrain.ELEC:
            if move_type == 'でんき':
                r = ut.round_half_up(r*5325/4096)
        case Terrain.GRASS:
            if move_type == 'くさ':
                r = ut.round_half_up(r*5325/4096)
        case Terrain.PSYCO:
            if move_type == 'エスパー':
                r = ut.round_half_up(r*5325/4096)
        case Terrain.MIST:
            if move.name == 'ミストバースト' and not attacker_mgr.is_floating():
                r = ut.round_half_up(r*1.5)

    if r != r0 and log:
        log.notes.append(f"フィールド x{r/r0:.1f}")

    # 防御側のフィールド補正
    r0 = r
    match self.battle.field_mgr.terrain(dfn):
        case Terrain.ELEC:
            if move.name == 'ライジングボルト':
                r = ut.round_half_up(r*2)
        case Terrain.GRASS:
            if move.name in ['じしん', 'じならし', 'マグニチュード']:
                r = ut.round_half_up(r*0.5)
        case Terrain.PSYCO:
            if move.name == 'ワイドフォース':
                r = ut.round_half_up(r*1.5)
        case Terrain.MIST:
            if move_type == 'ドラゴン':
                r = ut.round_half_up(r*0.5)

    if r != r0 and log:
        log.notes.append(f"フィールド x{r/r0:.1f}")

    # 防御側の特性
    r0 = r
    match defender_mgr.defending_ability(move).name:
        case 'かんそうはだ':
            if move_type == 'ほのお':
                r = ut.round_half_up(r*1.25)
            elif move_type == 'みず':
                r = 0
                self.battle.turn_mgr._move_was_negated_by_ability = True

        case 'たいねつ':
            if move_type == 'ほのお':
                r = ut.round_half_up(r*0.5)

    if r != r0 and log:
        log.notes.append(f"{defender.ability} x{r/r0:.1f}")

    return r
