from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..pokemon_manager import ActivePokemonManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Ailment, Condition, MoveCategory, \
    BoostSource, SideField, Weather, Terrain
from pokebot.common.constants import STAT_CODES
from pokebot.model import Move
from pokebot.logger.logger import TurnLog

from pokebot.core.move_utils import effective_move_type


def _activate_ability(self: ActivePokemonManager, move: Move | None) -> bool:
    opp = int(not self.idx)
    user = self.pokemon
    opponent = self.opponent
    opponent_mgr = self.battle.poke_mgrs[opp]

    activated = False

    # 追加効果扱い
    if move and opponent_mgr.can_receive_move_effect(move):
        match user.ability.name:
            case 'どくしゅ' | 'どくのくさり':
                activated = self.contacts(move) and \
                    self.battle.random.random() < 0.3 and \
                    opponent_mgr.set_ailment(Ailment.PSN, bad_poison=user.ability.name == 'どくのくさり')

    match user.ability.name:
        case 'アイスボディ':
            activated = self.battle.field_mgr.weather(self.idx) == Weather.SNOW and \
                self.add_hp(ratio=0.0625)
        case 'あめうけざら':
            activated = self.battle.field_mgr.weather(self.idx) == Weather.RAINY and \
                self.add_hp(ratio=0.0625)
        case 'あめふらし':
            activated = self.battle.field_mgr.set_weather(Weather.RAINY, self.idx)
        case 'すなおこし' | 'すなはき':
            activated = self.battle.field_mgr.set_weather(Weather.SAND, self.idx)
        case 'ひでり' | 'ひひいろのこどう':
            activated = self.battle.field_mgr.set_weather(Weather.SUNNY, self.idx)
        case 'ゆきふらし':
            activated = self.battle.field_mgr.set_weather(Weather.SNOW, self.idx)
        case 'かんそうはだ':
            weather = self.battle.field_mgr.weather(self.idx)
            sign = {Weather.SUNNY: -1, Weather.RAINY: +1}
            activated = weather in [Weather.SUNNY, Weather.RAINY] and \
                self.add_hp(ratio=sign[weather]/8)
        case 'あくしゅう':
            activated = self.battle.random.random() < 0.1
            if activated:
                self.battle.turn_mgr._flinch = True
        case 'いかく':
            if "anti_ikaku" in opponent.ability.tags:
                opponent_mgr.activate_ability()
                return False
            activated = opponent_mgr.add_rank(1, -1, by_opponent=True)
        case 'いかりのこうら':
            activated = self.berserk_triggered and self.add_rank(values=[0, 1, -1, 1, -1, 1])
        case 'いかりのつぼ':
            activated = self.battle.damage_mgr.critical and self.add_rank(1, +12)
        case 'うのミサイル':
            # TODO うのミサイル実装
            activated = False
        case 'うるおいボディ':
            activated = self.battle.field_mgr.weather(self.idx) == Weather.RAINY and self.set_ailment(Ailment.NONE)
        case 'だっぴ':
            activated = self.battle.random.random() < 0.3 and self.set_ailment(Ailment.NONE)
        case 'エレキメイカー' | 'ハドロンエンジン':
            activated = self.battle.field_mgr.set_terrain(Terrain.ELEC, self.idx)
        case 'グラスメイカー' | 'こぼれダネ':
            activated = self.battle.field_mgr.set_terrain(Terrain.GRASS, self.idx)
        case 'サイコメイカー':
            activated = self.battle.field_mgr.set_terrain(Terrain.PSYCO, self.idx)
        case 'ミストメイカー':
            activated = self.battle.field_mgr.set_terrain(Terrain.MIST, self.idx)
        case 'おもかげやどし':
            d = {'くさ': 5, 'ほのお': 1, 'みず': 4, 'いわ': 2}
            activated = self.types[0] in d and self.add_rank(d[self.types[0]], +1)
        case 'かそく':
            activated = self.active_turn and self.add_rank(5, +1)
        case 'かぜのり':
            activated = self.battle.field_mgr.count[SideField.OIKAZE][self.idx] and self.add_rank(1, +1)
        case 'かるわざ':
            user.ability.count += 1
            activated = True
        case 'がんじょう':
            activated = self.battle.turn_mgr.damage_dealt[opp] == user.stats[0]
            if activated:
                self.battle.turn_mgr.damage_dealt[opp] -= 1
        case 'かんろなみつ':
            opponent_mgr.add_rank(7, -1)
            activated = True
        case 'カーリーヘアー' | 'ぬめぬめ':
            activated = move and opponent_mgr.contacts(move) and self.add_rank(5, -1, by_opponent=True)
        case 'きもったま' | 'せいしんりょく' | 'どんかん' | 'マイペース':
            activated = True
        case 'ぎゃくじょう':
            activated = not self.berserk_triggered and self.add_rank(3, +1)
        case 'クォークチャージ' | 'こだいかっせい':
            if user.ability.name == "クォークチャージ":
                is_ability_activated = self.battle.field_mgr.terrain() == Terrain.ELEC
            else:
                is_ability_activated = self.battle.field_mgr.weather() == Weather.SUNNY

            if self.boost_source == BoostSource.NONE:
                # ブースト状態でない場合
                if is_ability_activated:
                    self.boost_source = BoostSource.ABILITY
                elif user.item.name == 'ブーストエナジー':
                    self.activate_item()
                else:
                    return False
            else:
                # ブースト状態の場合
                if not is_ability_activated:
                    # 外的要因がない場合
                    if user.item.name == 'ブーストエナジー':
                        self.activate_item()
                    else:
                        self.boost_source = BoostSource.NONE
                        self.battle.logger.append(TurnLog(self.battle.turn, self.idx, "ブースト解除"))
                        return False
                else:
                    return False

            activated = True
            self.battle.logger.append(TurnLog(self.battle.turn, self.idx,
                                              f"{STAT_CODES[self.boosted_idx]}上昇"))  # type: ignore
        case 'くだけるよろい':
            activated = move and move.category == MoveCategory.PHY and \
                opponent_mgr.add_rank(values=[0, 0, -1, 0, 0, 2])
        case 'こんがりボディ':
            self.add_rank(2, +2)
        case 'さまようたましい' | 'とれないにおい' | 'ミイラ':
            activated = move and opponent_mgr.contacts(move) and not self.is_ability_protected()
            if activated:
                if user.ability.name == 'さまようたましい':
                    user.ability.swap(opponent.ability)
                else:
                    opponent.ability.name = user.ability.name
        case 'さめはだ' | 'てつのトゲ':
            activated = move and \
                opponent_mgr.contacts(move) and \
                self.add_hp(ratio=-0.125)
        case 'サンパワー':
            activated = self.battle.field_mgr.weather(self.idx) == Weather.SUNNY and \
                self.add_hp(ratio=-0.125)
        case 'じきゅうりょく':
            activated = self.add_rank(2, +1)
        case 'じしんかじょう' | 'しろのいななき' | 'くろのいななき':
            stat_idx = 3 if user.ability.name == 'くろのいななき' else 1
            activated = opponent.hp == 0 and self.add_rank(stat_idx, +1)
        case 'しゅうかく':
            activated = user.item.name_lost[-2:] == 'のみ' and \
                (self.battle.field_mgr.weather(self.idx) == Weather.SUNNY or self.battle.random.random() < 0.5)
            if activated:
                user.item.active = True
        case 'じょうききかん':
            activated = move and \
                effective_move_type(self.battle, self.idx, move) in ['みず', 'ほのお'] and \
                self.add_rank(5, +6)
        case 'スロースタート':
            user.ability.count += 1
            if user.ability.count == 5:
                user.ability.active = False
        case 'せいぎのこころ' | 'ねつこうかん':
            t = 'あく' if opponent.ability.name == 'せいぎのこころ' else 'ほのお'
            activated = move and \
                effective_move_type(self.battle, opp, move) == t and \
                self.add_rank(1, +1)
        case 'せいでんき' | 'どくのトゲ' | 'ほのおのからだ' | 'ほうし':
            ailments = {'せいでんき': Ailment.PAR,
                        'どくのトゲ': Ailment.PSN,
                        'ほのおのからだ': Ailment.BRN,
                        'ほうし': self.battle.random.choice([Ailment.PSN, Ailment.PAR, Ailment.SLP])}
            activated = move and \
                opponent_mgr.contacts(move) and \
                self.battle.random.random() < 0.3 and \
                self.set_ailment(ailments[user.ability.name])
        case 'ゼロフォーミング':
            n = self.battle.field_mgr.set_weather(Weather.NONE, self.idx) + \
                self.battle.field_mgr.set_terrain(Terrain.NONE, self.idx)
            if n:
                self.battle.logger.insert(-n, TurnLog(self.battle.turn, self.idx, user.ability.name))
            activated = True
        case 'ダウンロード':
            eff_b = int(opponent.stats[2] * opponent_mgr.rank_modifier(2))
            eff_d = int(opponent.stats[4] * opponent_mgr.rank_modifier(4))
            activated = self.add_rank(1+2*int(eff_b > eff_d), +1)
        case 'ちくでん' | 'ちょすい' | 'どしょく':
            self.add_hp(ratio=0.25)
        case 'でんきエンジン':
            self.add_rank(5, +1)
        case 'でんきにかえる':
            activated = opponent_mgr.set_condition(Condition.CHARGE, 1)
        case 'どくげしょう':
            activated = move and \
                move.category == MoveCategory.PHY and \
                self.battle.field_mgr.add_count(SideField.DOKUBISHI, opp)
        case 'ナイトメア':
            activated = opponent.ailment == Ailment.SLP and \
                opponent_mgr.add_hp(ratio=-0.125)
        case 'のろわれボディ':
            activated = opponent_mgr.expended_moves and \
                self.battle.random.random() < 0.3 and \
                opponent_mgr.set_condition(Condition.KANASHIBARI, 4)
        case 'バリアフリー':
            for i in range(2):
                activated |= self.battle.field_mgr.set_field(SideField.REFLECTOR, i, 0)
                activated |= self.battle.field_mgr.set_field(SideField.LIGHTWALL, i, 0)
        case 'ばんけん':
            activated = opponent_mgr.add_rank(1, +1, by_opponent=True)
        case 'はんすう':
            activated = True
            user.ability.count += 1
            if user.ability.count == 1:
                # はんすう起動
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx, "はんすう起動"))
            elif user.ability.count == 3:
                # はんすう終了
                user.ability.count = 0
                self.battle.logger.append(TurnLog(self.battle.turn, self.idx, "はんすう終了"))
                if user.item.name_lost[-2:] == 'のみ':
                    user.item.active = True
                    # 強制消費
                    if not self.activate_item():
                        user.item.consume()
            else:
                return False
        case 'ひらいしん' | 'よびみず':
            self.add_rank(3, +1)
        case 'びびり':
            activated = move and \
                effective_move_type(self.battle, opp, move) in ['あく', 'ゴースト', 'むし'] and \
                self.add_rank(5, +1)
        case 'ふうりょくでんき':
            activated = move and \
                "wind" in move.tags and \
                not self.set_condition(Condition.CHARGE, 1)
        case 'ふくつのこころ':
            activated = self.add_rank(5, +1)
        case 'ふくつのたて':
            self.add_rank(2, +1)
            activated = True
        case 'ふとうのけん':
            self.add_rank(1, +1)
            activated = True
        case 'へんげんじざい' | 'リベロ' | 'へんしょく':
            if move:
                activated = self.types != [move.type] and \
                    move.type != 'ステラ' and \
                    not user.terastal
                if move.name in ['へんげんじざい', 'リベロ']:
                    activated &= user.ability.count == 0
                if activated:
                    self.lost_types += self.types
                    self.added_types += [move.type]
                    user.ability.count = 1
                    self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"-> {move.type}タイプ"))
        case 'ポイズンヒール':
            activated = user.ailment == Ailment.PSN
            if activated:
                self.add_hp(ratio=0.125)
        case 'ほおぶくろ':
            activated = self.add_hp(ratio=1/3)
        case 'ほろびのボディ':
            activated |= self.set_condition(Condition.HOROBI, 4)
            activated |= opponent_mgr.set_condition(Condition.HOROBI, 4)
        case 'マジシャン':
            activated = not user.item.active and \
                opponent.item and \
                opponent_mgr.is_item_removable()
            if activated:
                user.item.name = opponent.item.name
                opponent.item.active = False
        case 'みずがため':
            activated = move and \
                effective_move_type(self.battle, self.idx, move) == 'みず' and \
                self.add_rank(2, +2)
        case 'ムラっけ':
            up_idxs = [i for i in range(1, 6) if self.rank[i] < 6]
            if (activated := any(up_idxs)):
                # 能力上昇
                up_idx = self.battle.random.choice(up_idxs)
                self.add_rank(up_idx, +2)
                down_idxs = [i for i in range(1, 6) if self.rank[i] > -6 and i != up_idx]
                # 能力下降
                if down_idxs:
                    self.add_rank(self.battle.random.choice(down_idxs), -1)
        case 'メロメロボディ':
            activated = self.battle.random.random() < 0.3 and \
                opponent_mgr.set_condition(Condition.MEROMERO, 1)
        case 'もらいび':
            user.ability.count += 1
        case 'ゆうばく':
            activated = user.hp == 0 and opponent_mgr.add_hp(ratio=-0.25)
        case 'わたげ':
            activated = self.add_rank(5, -1)

    if activated:
        self.battle.logger.insert(-1, TurnLog(self.battle.turn, self.idx, user.ability.name))
        user.ability.observed = True  # 観測
        if "one_time" in user.ability.tags:
            user.ability.active = False
        return True

    return False
