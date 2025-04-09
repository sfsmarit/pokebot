from __future__ import annotations

import json
import random

from pokebot.sv.pokeDB import PokeDB
from pokebot.sv.ability import Ability
from pokebot.sv.item import Item
from pokebot.sv.pokemon import Pokemon
from pokebot.sv.battle import Battle, BattleMode, CommandRange
import pokebot.sv.utils as ut


class Player:
    """プレイヤーを表現するクラス"""

    def __init__(self):
        self.team = []                  # パーティ [Pokemon]
        self.n_game = 0                 # 試合数
        self.n_won = 0                  # 勝利数
        self.rating = 1500              # レート
        self.idx = None                 # 対戦相手と区別するためのindex

    def random_command(self, battle: Battle) -> int | list[int]:
        """ランダムなコマンドを返す"""
        if battle.phase == 'selection':
            return random.sample(battle.available_commands(self.idx), battle.n_selection)
        else:
            return random.choice(battle.available_commands(self.idx))

    def selection_command(self, battle: Battle) -> list[int]:
        """選出の方策関数"""
        return self.random_command(battle)

    def battle_command(self, battle: Battle) -> int:
        """ターン行動の方策関数"""
        return self.random_command(battle)

    def switch_command(self, battle: Battle) -> int:
        """自由交代の方策関数"""
        return self.random_command(battle)

    def complement_opponent_selection(self, battle: Battle):
        """相手の選出情報を補完する"""
        # 開示されていないポケモンの補完 (必須ではない)
        opponent = battle.player[not self.idx]
        selection_indexes = battle.selection_indexes[not self.idx]
        n = battle.n_selection

        if len(selection_indexes) <= n:
            unobserved_indexes = [
                i for i in range(len(opponent.team)) if i not in selection_indexes
            ]
            random.shuffle(unobserved_indexes)
            selection_indexes += unobserved_indexes[:n -
                                                    len(selection_indexes)]

        # 技の補完 (一つ以上の技が必要)
        for idx in selection_indexes:
            p = opponent.team[idx]
            if not p.moves:
                p.add_move('テラバースト')

    def complement_opponent_move(self, battle: Battle) -> str:
        """相手の技選択が開示されていない場合に補完する"""
        available_commands = battle.available_commands(not self.idx, phase='battle')  # phaseを指定する

        moves = [battle.pokemon[not self.idx].moves[cmd] for cmd
                 in available_commands if cmd in CommandRange['move']]

        if not moves:
            # ! Error
            print('-'*50)
            for pidx in [battle.first_player_idx, not battle.first_player_idx]:
                print(f'\tPlayer {int(pidx)}',
                      battle.log[pidx], battle.damage_log[pidx])
            for move in battle.pokemon[not self.idx].moves:
                print(f"{move} {battle.can_choose_move(not self.pidx, move)}")
            raise Exception("Empty move")

        return random.choice(moves)

    def complement_opponent_switch(self, battle: Battle) -> int:
        """相手の交代先が開示されていない場合に補完する"""
        return random.choice(battle.available_commands(not self.idx))

    def complement_pokemon(self, p: Pokemon, kata: str = '',
                           overwrite_nature: bool = True, overwrite_ability: bool = True,
                           overwrite_item: bool = True, overwrite_terastal: bool = True,
                           overwrite_move: bool = True, overwrite_effort: bool = True):
        """ポケモンの情報を補完する"""
        name = p.name

        # 型データに登録されている名前に変換する
        if name in PokeDB.valid_name_for_kata:
            name = PokeDB.valid_name_for_kata[name]

        # 型データがあれば優先して参照し、なければポケモンHOMEの統計データを参照する
        if name in PokeDB.name2kata:
            # 指定された型が見つからなければ、最も数が多い型を参照する
            if kata not in PokeDB.kata:
                kata = list(PokeDB.name2kata[name].keys())[0]

            nature = p.nature  # TODO 型データに性格を追加
            ability = Ability(list(PokeDB.kata[kata]['abilities'].keys())[0])
            item = Item(list(PokeDB.kata[kata]['items'].keys())[0])
            terastal = list(PokeDB.kata[kata]['terastals'].keys())[0]
            moves = PokeDB.kata[kata]['moves']
            effort = p.effort  # TODO 型データに努力値を追加

        elif name in PokeDB.home:
            nature = PokeDB.home[self.name]['nature'][0]
            ability = Ability(PokeDB.home[self.name]['ability'][0])
            item = Item(PokeDB.home[self.name]['item'][0])
            terastal = PokeDB.home[self.name]['terastal'][0]
            moves = PokeDB.home[self.name]['move'][:4]
            effort = p.effort  # 努力値の情報なし

        if overwrite_nature:
            p.nature = nature

        if overwrite_ability and not p.ability.observed:
            p.ability.org_name = ability

        if overwrite_item and not p.item.observed:
            p.item = item

        if overwrite_terastal and not p.terastal:
            p.terastal = terastal

        if overwrite_move:
            for move in moves:
                if len(p.moves) == 4:
                    break
                p.add_move(move)

        # if overwrite_effort:
        #    p.effort = effort

    def reject_items(self, battle: Battle):
        """開示されている情報から、棄却されるアイテムを更新する"""
        pidx = not self.idx

        observed_items = [p.item.name or p.item.name_lost for p in
                          battle.selected_pokemons(pidx) if p.item.observed]

        for p in battle.player[pidx].team:
            p.rejected_item_names.clear()

            # アイテムが観測されていたらスキップ
            if p.item.observed:
                continue

            if observed_items:
                p.rejected_item_names += observed_items

            # こだわり判定
            move_names = list(set([move.name for move in p.expended_moves]))
            if len(move_names) > 1:
                p.rejected_item_names += ['こだわりスカーフ', 'こだわりハチマキ', 'こだわりメガネ']

            # チョッキ判定
            if 'sta' in [move.cls for move in p.expended_moves]:
                p.rejected_item_names += ['とつげきチョッキ']

            # print(f"\tPlayer_{self.idx} {p.name} 棄却 {p.rejected_item_names}")

    def estimate_opponent_stats(self, battle: Battle):
        """相手が選出したポケモンのステータスとアイテムを推定値に置き換える
        Parameters
        ----------
        battle: Battle

        Returns
        ----------
            True: 更新が行われた、または現状のままで矛盾しない
            False: 推定失敗
        """

        # 相手の選出すべてに対して推定を行う
        for p in battle.selected_pokemons(not self.idx):

            # 素早さ、火力、耐久の順に推定する
            for stat_idx in [5, 1, 3, 2, 4]:
                # print(f"{p.name} {PokeDB.stats_kanji[stat_idx]} {p.nature} {p.effort[stat_idx]} {p.item=}")

                match stat_idx:
                    case 1 | 3:
                        return self.estimate_AC(battle=battle, p=p, stat_idx=stat_idx)
                    case 2 | 4:
                        return self.estimate_BD(battle=battle, p=p, stat_idx=stat_idx)
                    case 5:
                        self.estimate_S(p)

                # print(f"\t---> {p.nature} {p.effort[stat_idx]} {p.item=}")

    def estimate_AC(self, battle: Battle, p: Pokemon, stat_idx: int, count: int = 0) -> bool:
        pidx = not self.idx                         # 相手プレイヤーインデックス
        cls = 'phy' if stat_idx == 1 else 'spe'    # 技の分類

        errors = []

        # ダメージ履歴を参照する
        for dmg in battle.damage_history:
            # 推定に使えない条件
            if dmg.attack_player_idx != pidx or dmg.pokemon[pidx].name != p.name or \
                    dmg.pokemon[not pidx].eff_move_class(dmg.move) != cls or dmg.move.name in ['イカサマ', 'ボディプレス']:
                continue

            if count == 0:
                # 1度目の計算では、ダメージが発生した状況を再現する
                btl = Battle(damage=dmg, open_sheet=battle.open_sheet)
                btl.damage_history = battle.damage_history
            else:
                # 2度目以降は渡されたbattleをそのまま使う
                btl = battle

            # 非公開情報の削除
            if count == 0 and not btl.open_sheet:
                btl.pokemon[pidx].mask()

            # 推定されるダメージ
            oneshot_damages = btl.oneshot_damages(
                pidx, dmg.move, critical=dmg.critical)

            if oneshot_damages[0] > dmg.damage:
                # 推定ダメージが過大 = 火力を過大評価
                errors.append(+1)
            elif oneshot_damages[-1] < dmg.damage:
                # 推定ダメージが過小 = 火力を過小評価
                errors.append(-1)
            else:
                errors.append(0)

        # 該当するダメージ履歴なし
        if not errors:
            return False

        # 観測値と矛盾がなければ終了
        if not any(errors):
            return True

        # 評価結果が不自然なら中止
        if +1 in errors and -1 in errors:
            # print(f"{PokeDB.stats_kanji[stat_idx]}を推定できません")
            return False

        if count:
            return False

        # 探索範囲 (低->高火力)
        # 0
        # 252
        # +252
        # こだわり252
        # こだわり+252

        pc = btl.pokemon[pidx]

        # 性格
        nn = pc.nature if PokeDB.nature_corrections[pc.nature][stat_idx] == 1 else 'まじめ'
        nu = 'いじっぱり' if cls == 'phy' else 'ひかえめ'
        natures = [nn, nn, nu]

        # 努力値
        efforts = [0, 252, 252]

        # アイテム
        items = [pc.item]*3

        # アイテムが観測されていなければ、探索条件を追加する
        if not pc.item.observed:
            if 'こだわり' not in ''.join(pc.rejected_item_names):
                natures += [nn, nu]
                efforts += [252, 252]
                items += [Item('こだわりハチマキ' if cls == 'phy' else 'こだわりメガネ')]*2

        # 火力を過大評価しているなら、探索順を逆にする
        if +1 in errors:
            natures.reverse()
            efforts.reverse()
            items.reverse()

        # 現状の火力指数を計算
        eff_stats = pc.stats[stat_idx]

        match pc.item.name:
            case 'こだわりハチマキ':
                if cls == 'phy':
                    eff_stats *= pc.item.power_correction
            case 'こだわりメガネ':
                if cls == 'spe':
                    eff_stats *= pc.item.power_correction

        # 探索
        for nature, effort, item in zip(natures, efforts, items):
            pc.nature = nature
            pc.set_effort(stat_idx, effort)
            pc.item = item

            st = pc.stats[stat_idx]

            match item.name:
                case 'こだわりハチマキ':
                    if cls == 'phy':
                        st *= item.power_correction
                case 'こだわりメガネ':
                    if cls == 'spe':
                        st *= item.power_correction

            if +1 in errors:
                # 火力を過大評価していれば、現状以上の火力指数は検証しない
                if st > eff_stats:
                    continue
            else:
                # 火力を過小評価していれば、現状以下の火力指数は検証しない
                if st < eff_stats:
                    continue

            # 探索条件がダメージ履歴に合致すれば、元のポケモンを更新する
            if self.estimate_AC(battle=btl, p=pc, stat_idx=stat_idx, count=count+1):
                p.nature = nature
                p.set_effort(stat_idx, effort)
                p.item = item
                return True

        return False

    def estimate_BD(self, battle: Battle, p: Pokemon, stat_idx: int, count: int = 0) -> bool:
        pidx = not self.idx                         # 相手プレイヤーインデックス
        cls = 'phy' if stat_idx == 1 else 'spe'    # 技の分類

        errors = []

        # ダメージ履歴を参照する
        for dmg in battle.damage_history:
            # 推定に使えない条件
            if dmg.attack_player_idx == pidx or \
                    dmg.pokemon[pidx].name != p.name or \
                    dmg.pokemon[not pidx].eff_move_class(dmg.move) != cls or \
                    dmg.move.name in PokeDB.move_category['physical']:
                continue

            if count == 0:
                # 1度目の計算では、ダメージが発生した状況を再現する
                btl = Battle(damage=dmg, open_sheet=battle.open_sheet)
                btl.damage_history = battle.damage_history
            else:
                # 2度目以降は渡されたbattleをそのまま使う
                btl = battle

            # 非公開情報の削除
            if count == 0 and not btl.open_sheet:
                btl.pokemon[pidx].mask()

            # 推定されるダメージ
            oneshot_damages = btl.oneshot_damages(
                not pidx, dmg.move, critical=dmg.critical)
            damage_ratios = [round(d/btl.pokemon[pidx].stats[0], 2)
                             for d in oneshot_damages]

            if damage_ratios[0] > dmg.damage_ratio:
                # 推定ダメージが過大 = 耐久を過小評価
                errors.append(-1)
            elif damage_ratios[-1] < dmg.damage_ratio:
                # 推定ダメージが過小 = 耐久を過大評価
                errors.append(+1)
            else:
                errors.append(0)

        # 該当するダメージ履歴なし
        if not errors:
            return False

        # 観測値と矛盾がなければ終了
        if not any(errors):
            return True

        # 評価結果が不自然なら中止
        if +1 in errors and -1 in errors:
            print(f"{PokeDB.stats_kanji[stat_idx]}を推定できません")
            return False

        if count:
            return False

        # 探索範囲 (低->高耐久)
        # 0
        # H252
        # B/D252
        # HB/D252
        # HB/D+252
        # H252 とつげきチョッキ
        # HD252 とつげきチョッキ

        pc = btl.pokemon[pidx]

        # 性格
        nn = pc.nature if PokeDB.nature_corrections[pc.nature][stat_idx] == 1 else 'まじめ'
        if PokeDB.nature_corrections[pc.nature][1] == 0.9:
            nu = 'ずぶとい' if cls == 'phy' else 'おだやか'
        elif PokeDB.nature_corrections[pc.nature][3] == 0.9:
            nu = 'わんぱく' if cls == 'phy' else 'しんちょう'
        else:
            nu = 'のんき' if cls == 'phy' else 'なまいき'

        natures = [nn, nn, nn, nn, nu]

        # 努力値
        efforts_H = [0, 252, 0, 252, 252]
        efforts = [0, 0, 252, 252, 252]

        # アイテム
        items = [pc.item]*5

        # アイテムが観測されていなければ、探索条件を追加する
        if not pc.item.observed:
            if cls == 'spe' and 'とつげきチョッキ' not in pc.rejected_item_names:
                natures += [nn, nu]
                efforts += [252, 252]
                items += [Item('とつげきチョッキ')]*2

        # 耐久を過大評価しているなら探索順を逆にする
        if +1 in errors:
            natures.reverse()
            efforts_H.reverse()
            efforts.reverse()
            items.reverse()

        # 現状の耐久指数を計算
        eff_stats = pc.stats[0] * pc.stats[stat_idx]

        match pc.item.name:
            case 'とつげきチョッキ':
                if cls == 'spe':
                    eff_stats *= 1.5

        # 探索
        for nature, effort, effort_H, item in zip(natures, efforts, efforts_H, items):
            pc.nature = nature
            pc.set_effort(stat_idx, effort)
            pc.set_effort(0, effort_H)
            pc.item = item

            st = pc.stats[0] * pc.stats[stat_idx]

            match item.name:
                case 'とつげきチョッキ':
                    if cls == 'spe':
                        st *= 1.5

            if +1 in errors:
                # 耐久を過大評価していれば、現状以上の耐久指数は検証しない
                if st > eff_stats:
                    print("スキップ 過大")
                    continue
            else:
                # 耐久を過小評価していれば、現状以下の耐久指数は検証しない
                if st < eff_stats:
                    print("スキップ 過小")
                    continue

            # 探索条件がダメージ履歴に整合すればポケモンを更新する
            if self.estimate_BD(battle=btl, p=pc, stat_idx=stat_idx, count=count+1):
                p.nature = nature
                p.set_effort(stat_idx, effort)
                p.set_effort(0, effort_H)
                p.item = item
                return True

        return False

    def estimate_S(self, p: Pokemon) -> bool:
        """speed_rangeからステータスと持ち物を推定する"""
        if p.speed_range[0] <= p.stats[5] <= p.speed_range[1]:
            return True

        v = p.speed_range[0] if p.stats[5] < p.speed_range[0] else p.speed_range[1]

        # スカーフ判定
        if v > Pokemon.calculate_stats(p.name, 'ようき', efforts=[0]*5+[252])[5]:
            p.item = Item('こだわりスカーフ')
            v = ut.round_half_up(v/1.5)

        # 努力値推定
        ac = [p.stats[1], p.stats[3]]
        if ac.index(max(ac)) == 0:
            natures = ['ようき', 'いじっぱり', 'ゆうかん', 'まじめ']
        else:
            natures = ['おくびょう', 'ひかえめ', 'れいせい', 'まじめ']

        efforts_50 = [0] + [4+8*i for i in range(32)]
        efforts_50.reverse()

        for nature in natures:
            a = [Pokemon.calculate_stats(p.name, nature, efforts=[0]*5+[eff])[5]
                 for eff in efforts_50]
            for i in range(len(a[:-1])):
                if a[i+1] <= v <= a[i]:
                    p.nature = nature
                    p.set_stats(5, a[i])
                    return True

        return False

    ######################## ファイル入出力 ########################
    def save_team(self, filename: str):
        """パーティをファイルに保存"""
        with open(filename, 'w', encoding='utf-8') as fout:
            d = {}
            for i, p in enumerate(self.team):
                d[str(i)] = p.dump()
                print(f"{i+1} {p}\n")
            fout.write(json.dumps(d, ensure_ascii=False))

    def load_team(self, filename: str):
        """ファイルからパーティを読み込む"""
        with open(filename, encoding='utf-8') as fin:
            dict = json.load(fin)
            self.team = []
            for i, d in enumerate(dict.values()):
                p = Pokemon()
                p.load(d)
                self.team.append(p)
                print(f"{i+1} {p}\n")

    ######################## 対戦 ########################
    def update_rating(self, opponent: Player, won: bool = True):
        """自分と相手のレートを更新する"""
        players = [self, opponent]
        EAs = []

        for i in range(2):
            EAs.append(
                1 / (1+10**((players[not i].rating - players[i].rating)/400)))

        for i in range(2):
            players[i].rating += 32 * ((won+i) % 2 - EAs[i])

    def game(self, opponent: Player = None, mode: int = BattleMode.SIM,
             n_selection: int = 3, open_sheet: bool = False, max_turn=999,
             seed: int = None, video_id: int = 0, mute: bool = False):
        """試合を行う

        Parameters
        ----------
        opponent: Player
            対戦相手のプレイヤー

        mode: int
            対戦モード
                BattleMode.SIM             # シミュレーション
                BattleMode.OFFLINE         # 実機 学校最強大会
                BattleMode.ONLINE          # 実機 オンライン対戦

        n_selection: int
            選出するポケモンの数

        open_sheet: bool
            Trueならお互いのパーティを公開

        seed: int
            ゲーム内乱数のシード

        mute: bool
            Trueなら標準出力しない

        Returns
        ----------
        Battleインスタンス
        """

        # レベルを50に修正
        if mode != BattleMode.OFFLINE:
            for p in self.team:
                p.level = 50

        if not opponent:
            if mode == BattleMode.SIM:
                raise Exception(
                    "Opponent player is requred to run in BattleMode.SIM mode")
            else:
                opponent = Player()

        # Battleインスタンスを生成
        battle = Battle(player1=self, player2=opponent, mode=mode, n_selection=n_selection,
                        open_sheet=open_sheet, max_turn=max_turn, seed=seed, video_id=video_id,
                        mute=mute)

        if mode != BattleMode.SIM:
            # 実機対戦
            battle.main_loop()

        else:
            # シミュレーション
            while battle.winner is None:
                # 勝敗が決まるまでターンを進める
                battle.proceed_turn()

                # ログ表示
                if not mute:
                    print(f'ターン{battle.turn}')
                    for pidx in [battle.first_player_idx, not battle.first_player_idx]:
                        print(f'\tPlayer {int(pidx)}',
                              battle.log[pidx], battle.damage_log[pidx])

        # 戦績の更新
        self.n_game += 1
        opponent.n_game += 1

        if battle.winner == 0:
            self.n_won += 1
        else:
            opponent.n_won += 1

        # レート更新
        self.update_rating(opponent, won=(battle.winner == 0))

        return battle
