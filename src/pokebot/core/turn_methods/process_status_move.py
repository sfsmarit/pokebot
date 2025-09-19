from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Ailment, Condition, \
    GlobalField, SideField, Weather, Terrain
import pokebot.common.utils as ut
from pokebot.model import Pokemon, Move
from pokebot.logger import TurnLog


def _process_status_move(self: TurnManager,
                         atk: PlayerIndex | int,
                         move: Move):
    battle = self.battle

    org_dfn = dfn = int(not atk)
    attacker = battle.pokemons[atk]
    defender = battle.pokemons[dfn]
    attacker_mgr = battle.poke_mgrs[atk]
    defender_mgr = battle.poke_mgrs[dfn]

    # マジックミラー判定
    self._move_was_mirrored = move.mirror and \
        defender_mgr.defending_ability(move) == 'マジックミラー'

    if self._move_was_mirrored:
        defender.ability.observed = True  # 観測
        battle.logger.append(TurnLog(battle.turn, dfn, defender.ability.name))

        # 攻守入れ替え
        atk, dfn = dfn, atk
        attacker = battle.pokemons[atk]
        defender = battle.pokemons[dfn]
        attacker_mgr = battle.poke_mgrs[atk]
        defender_mgr = battle.poke_mgrs[dfn]

    # みがわりによる無効判定
    if defender_mgr.sub_hp and move.subst:
        self.move_succeeded[atk] = False
        return

    # タイプ相性・特性による無効判定
    if move.gold:
        self.move_succeeded[atk] = bool(battle.damage_mgr.damage_modifier(atk, move))

        if defender_mgr.defending_ability(move) == 'おうごんのからだ':
            self.move_succeeded[atk] = False
            defender.ability.observed = True  # 観測

        if not self.move_succeeded[atk]:
            return

    match move.name:
        case 'アクアリング':
            self.move_succeeded[atk] = attacker_mgr.set_condition(Condition.AQUA_RING)
        case 'あくまのキッス' | 'うたう' | 'キノコのほうし' | 'くさぶえ' | 'さいみんじゅつ' | 'ダークホール' | 'ねむりごな':
            self.move_succeeded[atk] = defender_mgr.set_ailment(Ailment.SLP, move)
        case 'あくび':
            self.move_succeeded[atk] = defender_mgr.set_condition(Condition.NEMUKE, 2, move) and dfn == org_dfn
        case 'あさのひざし' | 'こうごうせい' | 'じこさいせい' | 'すなあつめ' | 'タマゴうみ' | 'つきのひかり' | 'なまける' | 'はねやすめ' | 'ミルクのみ':
            r = 0.5
            match move.name:
                case 'すなあつめ':
                    if battle.field_mgr.weather() == Weather.SAND:
                        r = 2732/4096
                case 'あさのひざし' | 'こうごうせい' | 'つきのひかり':
                    match battle.field_mgr.weather(atk):
                        case Weather.SUNNY:
                            r = 0.75
                        case Weather.RAINY | Weather.SNOW | Weather.SAND:
                            r = 0.25
            self.move_succeeded[atk] = attacker_mgr.add_hp(ut.round_half_down(r*attacker.stats[0]))
            # 飛行タイプ消失
            if move.name == 'はねやすめ' and \
                    self.move_succeeded[atk] and \
                    not attacker.terastal and \
                    'ひこう' in attacker_mgr.types:
                attacker_mgr.lost_types.append('ひこう')
        case 'あまいかおり':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(7, -1, by_opponent=True)) and dfn == org_dfn
        case 'あまえる':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(1, -2, by_opponent=True)) and dfn == org_dfn
        case 'あまごい':
            self.move_succeeded[atk] = battle.field_mgr.set_weather(Weather.RAINY, atk)
        case 'すなあらし':
            self.move_succeeded[atk] = battle.field_mgr.set_weather(Weather.SAND, atk)
        case 'にほんばれ':
            self.move_succeeded[atk] = battle.field_mgr.set_weather(Weather.SUNNY, atk)
        case 'ゆきげしき':
            self.move_succeeded[atk] = battle.field_mgr.set_weather(Weather.SNOW, atk)
        case 'あやしいひかり' | 'いばる' | 'おだてる' | 'ちょうおんぱ' | 'てんしのキッス' | 'フラフラダンス':
            self.move_succeeded[atk] = defender_mgr.set_condition(
                Condition.CONFUSION, self.battle.random.randint(2, 5), move)
            match move.name:
                case 'いばる':
                    defender_mgr.add_rank(1, +2, by_opponent=True)
                case 'おだてる':
                    defender_mgr.add_rank(3, +1, by_opponent=True)
        case 'アロマセラピー' | 'いやしのすず':
            selected = battle.selected_pokemons(atk)
            self.move_succeeded[atk] = any([p.ailment for p in selected])
            if self.move_succeeded[atk]:
                # 場のポケモンの状態異常を回復
                attacker_mgr.set_ailment(Ailment.NONE)
                # 控えのポケモンの状態異常を回復
                for p in selected:
                    if p is not attacker:
                        p.ailment = Ailment.NONE
        case 'アンコール':
            self.move_succeeded[atk] = defender_mgr.set_condition(Condition.ENCORE, 3, move)
            if self.move_succeeded[atk]:
                # 相手が後手なら技を書き換える
                if dfn != battle.turn_mgr.first_player_idx:
                    self.move[dfn] = defender_mgr.expended_moves[-1]
                self.move_succeeded[atk] = (dfn == org_dfn)
        case 'いえき' | 'シンプルビーム' | 'なかまづくり' | 'なやみのタネ':
            self.move_succeeded[atk] = not defender_mgr.is_ability_protected()
            if self.move_succeeded[atk]:
                match move.name:
                    case 'いえき':
                        self.move_succeeded[atk] = defender.ability.active
                        defender.ability.active = False
                    case 'シンプルビーム':
                        self.move_succeeded[atk] = defender.ability.name != 'たんじゅん'
                        defender.ability.name = 'たんじゅん'
                    case 'なかまづくり':
                        self.move_succeeded[atk] = attacker.ability.name != defender.ability.name
                        defender.ability.name = attacker.ability.name
                    case 'なやみのタネ':
                        self.move_succeeded[atk] = defender.ability.name != 'ふみん'
                        defender.ability.name = 'ふみん'
            self.move_succeeded[atk] &= dfn == org_dfn
        case 'いたみわけ':
            h = int((attacker.hp + defender.hp)/2)
            self.move_succeeded[atk] = h > attacker.hp
            for i in range(2):
                battle.poke_mgrs[i].add_hp(h - battle.pokemons[i].hp, move=move)
        case 'いとをはく' | 'こわいかお' | 'わたほうし':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(5, -2, by_opponent=True)) and dfn == org_dfn
        case 'いやしのはどう' | 'フラワーヒール':
            r = 0.5
            match move.name:
                case 'いやしのはどう':
                    if attacker.ability.name == 'メガランチャー':
                        r = 0.75
                case 'フラワーヒール':
                    if battle.field_mgr.terrain(atk) == Terrain.GRASS:
                        r = 0.75
            self.move_succeeded[atk] = defender_mgr.add_hp(ut.round_half_up(defender.stats[0]*r))
        case 'いやなおと':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(2, -2, by_opponent=True)) and dfn == org_dfn
        case 'うそなき':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(4, -2, by_opponent=True)) and dfn == org_dfn
        case 'うつしえ' | 'なりきり':
            self.move_succeeded[atk] = not attacker_mgr.is_ability_protected() and \
                "unreproducible" in defender.ability.tags and \
                attacker.ability.name != defender.ability.name
            if self.move_succeeded[atk]:
                attacker.ability.name = defender.ability.name
        case 'うらみ':
            self.move_succeeded[atk] = len(defender_mgr.expended_moves) > 0 and \
                (expended_move := defender_mgr.expended_moves[-1]) is not None and \
                expended_move.pp > 0
            if self.move_succeeded[atk]:
                expended_move.add_pp(-4)
                battle.logger.append(TurnLog(battle.turn, atk, f"{expended_move} PP {expended_move.pp}"))
        case 'エレキフィールド':
            self.move_succeeded[atk] = battle.field_mgr.set_terrain(Terrain.ELEC, atk)
        case 'グラスフィールド':
            self.move_succeeded[atk] = battle.field_mgr.set_terrain(Terrain.GRASS, atk)
        case 'サイコフィールド':
            self.move_succeeded[atk] = battle.field_mgr.set_terrain(Terrain.PSYCO, atk)
        case 'ミストフィールド':
            self.move_succeeded[atk] = battle.field_mgr.set_terrain(Terrain.MIST, atk)
        case 'えんまく' | 'すなかけ':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(6, -1, by_opponent=True)) and dfn == org_dfn
        case 'おいかぜ':
            self.move_succeeded[atk] = battle.field_mgr.set_field(SideField.OIKAZE, atk, 4)
            if self.move_succeeded[atk]:
                match attacker.ability.name:
                    case 'かぜのり':
                        attacker_mgr.activate_ability(mode="rank")
                    case 'ふうりょくでんき':
                        attacker_mgr.activate_ability(move)
        case 'オーロラベール':
            self.move_succeeded[atk] = battle.field_mgr.weather() == Weather.SNOW
            if self.move_succeeded[atk]:
                count = 8 if attacker.item.name == 'ひかりのねんど' else 5
                self.move_succeeded[atk] = battle.field_mgr.set_field(SideField.REFLECTOR, count=count)
                self.move_succeeded[atk] |= battle.field_mgr.set_field(SideField.LIGHT_WALL, count=count)
        case 'おかたづけ' | 'りゅうのまい':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(values=[0, 1, 0, 0, 0, 1]))
            if move.name == 'おかたづけ':
                for field in [SideField.MAKIBISHI, SideField.DOKUBISHI, SideField.STEALTH_ROCK, SideField.NEBA_NET]:
                    for i in range(2):
                        self.move_succeeded[atk] |= battle.field_mgr.set_field(field, i, 0)
        case 'おきみやげ':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(values=[0, -2, 0, -2], by_opponent=True))
            attacker.hp = 0
        case 'おたけび' | 'なみだめ':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(values=[0, -1, 0, -1], by_opponent=True)) and dfn == org_dfn
        case 'おにび':
            self.move_succeeded[atk] = defender_mgr.set_ailment(Ailment.BRN, move)
        case 'かいでんぱ':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(3, -2, by_opponent=True)) and dfn == org_dfn
        case 'かいふくふうじ':
            self.move_succeeded[atk] = defender_mgr.set_condition(Condition.HEAL_BLOCK, 5, move) and dfn == org_dfn
        case 'かえんのまもり' | 'スレッドトラップ' | 'トーチカ' | 'ニードルガード' | 'まもる' | 'みきり':
            battle.turn_mgr._protecting_move = move
        case 'かげぶんしん':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(7, +1))
        case 'かたくなる' | 'からにこもる' | 'まるくなる':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(2, +1))
        case 'かなしばり':
            self.move_succeeded[atk] = defender_mgr.set_condition(Condition.KANASHIBARI, 4, move) and dfn == org_dfn
        case 'からをやぶる':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(values=[0, 2, -1, 2, -1, 2]))
        case 'きあいだめ':
            self.move_succeeded[atk] = attacker_mgr.set_condition(Condition.CRITICAL, 2)
        case 'ギアチェンジ':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(values=[0, 1, 0, 0, 0, 2]))
        case 'きりばらい':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(7, -1, by_opponent=True))
            self.move_succeeded[atk] |= battle.field_mgr.set_terrain(Terrain.NONE, atk)
            for field in [SideField.REFLECTOR, SideField.LIGHT_WALL, SideField.SHINPI, SideField.WHITE_MIST]:
                self.move_succeeded[atk] |= battle.field_mgr.set_field(field, dfn, 0)
            for field in [SideField.MAKIBISHI, SideField.DOKUBISHI, SideField.STEALTH_ROCK, SideField.NEBA_NET]:
                self.move_succeeded[atk] |= battle.field_mgr.set_field(field, atk, count=0)
                self.move_succeeded[atk] |= battle.field_mgr.set_field(field, dfn, count=0)
            self.move_succeeded[atk] &= dfn == org_dfn
        case 'きんぞくおん':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(4, -2, by_opponent=True)) and dfn == org_dfn
        case 'くすぐる':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(values=[0, -1, -1])) and dfn == org_dfn
        case 'くろいきり':
            self.move_succeeded[atk] = False
            for i in range(2):
                self.move_succeeded[atk] |= any(battle.poke_mgrs[i].rank)
                battle.poke_mgrs[i].reset_rank()
        case 'くろいまなざし' | 'とおせんぼう':
            self.move_succeeded[atk] = defender_mgr.set_condition(Condition.SWITCH_BLOCK, move=move) and dfn == org_dfn
        case 'こうそくいどう' | 'ロックカット':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(5, +2))
        case 'コスモパワー' | 'ぼうぎょしれい':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(values=[0, 0, 1, 0, 1]))
        case 'コットンガード':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(2, +3))
        case 'こらえる':
            battle.turn_mgr._koraeru = True
            # 成否判定は被弾時に行う
            self.move_succeeded[atk] = False
        case 'さむいギャグ':
            battle.field_mgr.set_weather(Weather.SNOW, atk)
        case 'しっぽきり':
            self.move_succeeded[atk] = attacker_mgr.sub_hp == 0 and attacker.hp_ratio > 0.5
            if self.move_succeeded[atk]:
                attacker_mgr.add_hp(ratio=-0.5)
        case 'しっぽをふる' | 'にらみつける':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(2, -1, by_opponent=True)) and dfn == org_dfn
        case 'しびれごな' | 'でんじは' | 'へびにらみ':
            self.move_succeeded[atk] = defender_mgr.set_ailment(Ailment.PAR, move)
        case 'じこあんじ':
            self.move_succeeded[atk] = attacker_mgr.rank != defender_mgr.rank
            if self.move_succeeded[atk]:
                attacker_mgr.rank = defender_mgr.rank.copy()
        case 'ジャングルヒール' | 'みかづきのいのり':
            self.move_succeeded[atk] = attacker_mgr.add_hp(ratio=0.25)
            self.move_succeeded[atk] |= attacker_mgr.set_ailment(Ailment.NONE)
        case 'じゅうでん':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(4, +1))
            self.move_succeeded[atk] |= attacker_mgr.set_condition(Condition.CHARGE)
        case 'じゅうりょく':
            self.move_succeeded[atk] = battle.field_mgr.set_field(GlobalField.GRAVITY, count=5)
        case 'しょうりのまい':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(values=[0, 1, 1, 0, 0, 1]))
        case 'しろいきり':
            self.move_succeeded[atk] = battle.field_mgr.set_field(SideField.WHITE_MIST, atk, 5)
        case 'しんぴのまもり':
            self.move_succeeded[atk] = battle.field_mgr.set_field(SideField.SHINPI, atk, 5)
        case 'スキルスワップ':
            self.move_succeeded[atk] = not defender_mgr.is_ability_protected()
            if self.move_succeeded[atk]:
                attacker.ability.swap(defender.ability)
                for i in range(2):
                    battle.logger.append(TurnLog(battle.turn, i, f"-> {battle.pokemons[i].ability}"))
                # 特性の再発動
                for i in battle.turn_mgr.speed_order:
                    if "immediate" in battle.pokemons[i].ability.tags:
                        battle.poke_mgrs[i].activate_ability()
        case 'すてゼリフ':
            # 成否判定は交代時に行う
            defender_mgr.add_rank(values=[0, -1, 0, -1], by_opponent=True)
        case 'すりかえ' | 'トリック':
            self.move_succeeded[atk] = attacker_mgr.is_item_removable() and defender_mgr.is_item_removable()
            if self.move_succeeded[atk]:
                attacker.item.swap(defender.item)
                for i, poke in enumerate(battle.pokemons):
                    battle.logger.append(TurnLog(battle.turn, i, f"-> {poke.item}"))
                    # 即時発動アイテムの判定
                    if poke.item.immediate:
                        battle.poke_mgrs[i].activate_item()
        case 'せいちょう':
            v = 2 if battle.field_mgr.weather(atk) == Weather.SUNNY else 1
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(values=[0, 0, 0, v, v]))
        case 'ステルスロック':
            self.move_succeeded[atk] = battle.field_mgr.add_count(SideField.STEALTH_ROCK, dfn)
        case 'まきびし':
            self.move_succeeded[atk] = battle.field_mgr.add_count(SideField.MAKIBISHI, dfn)
        case 'どくびし':
            self.move_succeeded[atk] = battle.field_mgr.add_count(SideField.DOKUBISHI, dfn)
        case 'ねばねばネット':
            self.move_succeeded[atk] = battle.field_mgr.add_count(SideField.NEBA_NET, dfn)
        case 'ソウルビート':
            cost = int(attacker.stats[0]/3)
            self.move_succeeded[atk] = attacker.hp > cost
            if self.move_succeeded[atk]:
                attacker_mgr.add_hp(-cost)
                attacker_mgr.add_rank(values=[0]+[1]*5)
        case 'たくわえる':
            count = attacker_mgr.count[Condition.STOCK]
            self.move_succeeded[atk] = count < 3
            if self.move_succeeded[atk]:
                attacker_mgr.set_condition(Condition.STOCK,  count+1)
                any(attacker_mgr.add_rank(values=[0, 0, 1, 0, 1]))
        case 'たてこもる' | 'てっぺき' | 'とける':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(2, +2))
        case 'ちいさくなる':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(7, +2))
        case 'ちからをすいとる':
            self.move_succeeded[atk] = defender_mgr.rank[1] > -6
            if self.move_succeeded[atk]:
                attacker_mgr.add_hp(
                    attacker_mgr.hp_drain_amount(int(defender.stats[1] * defender_mgr.rank_modifier(1))))
                defender_mgr.add_rank(1, -1, by_opponent=True)
                self.move_succeeded[atk] = dfn == org_dfn
        case 'ちょうのまい':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(values=[0, 0, 0, 1, 1, 1]))
        case 'ちょうはつ':
            self.move_succeeded[atk] = defender_mgr.set_condition(Condition.CHOHATSU, 3, move=move) and dfn == org_dfn
        case 'つぶらなひとみ' | 'なかよくする' | 'なきごえ':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(1, -1, by_opponent=True)) and dfn == org_dfn
        case 'つぼをつく':
            indexes = [i for i in range(1, 8) if attacker_mgr.rank[i] < 6]
            self.move_succeeded[atk] = bool(indexes)
            if self.move_succeeded[atk]:
                attacker_mgr.add_rank(battle.random.choice(indexes), +2)
        case 'つめとぎ':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(values=[0, 1, 0, 0, 0, 0, 1]))
        case 'つるぎのまい':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(1, +2))
        case 'テクスチャー':
            self.move_succeeded[atk] = not attacker.terastal
            if self.move_succeeded[atk]:
                attacker_mgr.lost_types += attacker_mgr.types
                attacker_mgr.added_types = [attacker.moves[0].type]
                battle.logger.append(TurnLog(battle.turn, atk, f"-> {attacker_mgr.types[0]}タイプ"))
        case 'でんじふゆう':
            self.move_succeeded[atk] = attacker_mgr.set_condition(Condition.MAGNET_RISE, 5)
        case 'とおぼえ':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(1, +1))
        case 'どくどく' | 'どくのこな' | 'どくガス' | 'どくのいと':
            if move.name == 'どくのいと':
                defender_mgr.add_rank(5, -1, by_opponent=True)
            self.move_succeeded[atk] = defender_mgr.set_ailment(
                Ailment.PSN, move, bad_poison=(move.name == 'どくどく')) and dfn == org_dfn
        case 'とぐろをまく':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(values=[0, 1, 1, 0, 0, 0, 1]))
        case 'トリックルーム':
            count = 5 * (not battle.field_mgr.count[GlobalField.TRICKROOM])
            self.move_succeeded[atk] = battle.field_mgr.set_field(GlobalField.TRICKROOM, count=count)
        case 'ドわすれ':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(4, +2))
        case 'ないしょばなし':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(3, -1, by_opponent=True)) and dfn == org_dfn
        case 'ねがいごと':
            self.move_succeeded[atk] = battle.field_mgr.set_field(SideField.WISH, count=2)
        case 'ねごと':
            self.move_succeeded[atk] = False
        case 'ねむる':
            self.move_succeeded[atk] = attacker.hp_ratio < 1 and \
                attacker_mgr.count[Condition.HEAL_BLOCK] == 0 and \
                attacker_mgr.set_ailment(Ailment.SLP, move)
            if self.move_succeeded[atk]:
                attacker.hp = attacker.stats[0]
        case 'ねをはる':
            self.move_succeeded[atk] = attacker_mgr.set_condition(Condition.NEOHARU)
        case 'のろい':
            if 'ゴースト' in attacker_mgr.types:
                self.move_succeeded[atk] = defender_mgr.set_condition(Condition.NOROI, move=move)
                if self.move_succeeded[atk]:
                    attacker_mgr.add_hp(ratio=-0.5)
            else:
                self.move_succeeded[atk] = any(attacker_mgr.add_rank(values=[0, 1, 1, 0, 0, -1]))
        case 'ハートスワップ':
            self.move_succeeded[atk] = attacker_mgr.rank != defender_mgr.rank
            if self.move_succeeded[atk]:
                attacker_mgr.rank, defender_mgr.rank = defender_mgr.rank.copy(), attacker_mgr.rank.copy()
        case 'はいすいのじん':
            self.move_succeeded[atk] = attacker_mgr.set_condition(Condition.SWITCH_BLOCK)
            if self.move_succeeded[atk]:
                self.move_succeeded[atk] &= any(attacker_mgr.add_rank(values=[0, 1, 1, 1, 1, 1]))
        case 'ハバネロエキス':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(values=[0, 2, -2], by_opponent=True)) and dfn == org_dfn
        case 'はらだいこ':
            self.move_succeeded[atk] = attacker.hp_ratio > 0.5
            if self.move_succeeded[atk]:
                attacker_mgr.add_hp(ratio=-0.5)
                self.move_succeeded[atk] &= any(attacker_mgr.add_rank(1, 12))
        case 'ひかりのかべ' | 'リフレクター':
            count = 8 if attacker.item.name == 'ひかりのねんど' else 5
            field = SideField.LIGHT_WALL if move.name == "ひかりのかべ" else SideField.REFLECTOR
            self.move_succeeded[atk] = battle.field_mgr.set_field(field, atk, count)
        case 'ひっくりかえす':
            self.move_succeeded[atk] = any(defender_mgr.rank)
            if self.move_succeeded[atk]:
                defender_mgr.rank = [-v for v in defender_mgr.rank]
                self.move_succeeded[atk] = dfn == org_dfn
                battle.logger.append(TurnLog(battle.turn, atk, f"-> {Pokemon.rank2str(defender_mgr.rank)}"))
        case 'ビルドアップ':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(values=[0, 1, 1]))
        case 'フェザーダンス':
            self.move_succeeded[atk] = any(defender_mgr.add_rank(1, -2, by_opponent=True)) and dfn == org_dfn
        case 'ふきとばし' | 'ほえる':
            self.move_succeeded[atk] = defender_mgr.is_blowable()
            if self.move_succeeded[atk]:
                switch_idx = battle.random.choice(battle.switchable_indexes(dfn))
                battle.turn_mgr.switch_pokemon(dfn, switch_idx=switch_idx)
                self.move_succeeded[atk] = dfn == org_dfn
        case 'ふるいたてる':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(values=[0, 1, 0, 1]))
        case 'ブレイブチャージ' | 'めいそう':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(values=[0, 0, 0, 1, 1]))
            if move.name == 'ブレイブチャージ':
                attacker_mgr.set_ailment(Ailment.NONE)
        case 'ほおばる':
            self.move_succeeded[atk] = attacker.item.name[-2:] == 'のみ'
            if self.move_succeeded[atk]:
                if not attacker_mgr.activate_item():
                    attacker_mgr.consume_item()  # 強制消費
                attacker_mgr.add_rank(2, +2)
        case 'ほたるび':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(3, +3))
        case 'ほろびのうた':
            attacker_mgr.set_condition(Condition.HOROBI, 4)
            self.move_succeeded[atk] = defender_mgr.set_condition(Condition.HOROBI, 4, move=move) and dfn == org_dfn
        case 'まほうのこな' | 'みずびたし':
            t = {'まほうのこな': 'エスパー', 'みずびたし': 'みず'}
            self.move_succeeded[atk] = not defender.terastal and defender_mgr.types != [t[move.name]]
            if self.move_succeeded[atk]:
                defender_mgr.lost_types += defender_mgr.types.copy()
                defender_mgr.added_types = [t[move.name]]
        case 'みちづれ':
            attacker_mgr.set_condition(Condition.MICHIZURE)
        case 'ミラータイプ':
            self.move_succeeded[atk] = not attacker.terastal and attacker_mgr.types != defender_mgr.types
            if self.move_succeeded[atk]:
                attacker_mgr.lost_types += attacker_mgr.types
                attacker_mgr.added_types = defender_mgr.types
                battle.logger.append(TurnLog(battle.turn, atk, f"-> {attacker_mgr.types}タイプ"))
        case 'みがわり':
            cost = int(attacker.stats[0]/4)
            self.move_succeeded[atk] = attacker_mgr.sub_hp == 0 and attacker.hp > cost
            if self.move_succeeded[atk]:
                attacker_mgr.add_hp(-cost)
                attacker_mgr.sub_hp = cost
        case 'みをけずる':
            self.move_succeeded[atk] = attacker.hp_ratio > 0.5 and \
                any(attacker_mgr.add_rank(values=[0, 2, 0, 2, 0, 2]))
            if self.move_succeeded[atk]:
                attacker_mgr.add_hp(ratio=-0.5)
        case 'メロメロ':
            self.move_succeeded[atk] = defender_mgr.set_condition(Condition.MEROMERO, move=move) and dfn == org_dfn
        case 'もりののろい':
            self.move_succeeded[atk] = not defender.terastal and 'くさ' not in defender_mgr.types
            if self.move_succeeded[atk]:
                defender_mgr.added_types.append('くさ')
        case 'やどりぎのタネ':
            self.move_succeeded[atk] = defender_mgr.set_condition(Condition.YADORIGI, move=move) and dfn == org_dfn
        case 'リサイクル':
            self.move_succeeded[atk] = not attacker.item.active
            if self.move_succeeded[atk]:
                attacker.item.active = True
                battle.logger.append(TurnLog(battle.turn, atk, f"{attacker.item}回収"))
        case 'リフレッシュ':
            self.move_succeeded[atk] = attacker_mgr.set_ailment(Ailment.NONE)
        case 'ロックオン':
            self.move_succeeded[atk] = not attacker_mgr.lockon
            attacker_mgr.lockon = True
        case 'わるだくみ':
            self.move_succeeded[atk] = any(attacker_mgr.add_rank(3, +2))

    return
