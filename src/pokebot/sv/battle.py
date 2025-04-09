from __future__ import annotations

import time
import json
from copy import deepcopy
import random
import warnings
import os
import sys
import cv2
import glob
import os
import glob
import unicodedata
import shutil
from pathlib import Path
from importlib import resources

from pokebot.sv.pokeDB import PokeDB
from pokebot.sv.ability import Ability
from pokebot.sv.item import Item
from pokebot.sv.move import Move
from pokebot.sv.pokemon import Pokemon
from pokebot.sv.logger import BattleLogger, DamageLogger
import pokebot.sv.utils as ut
from pokebot.sv.constants import Gender, BattleMode


# TODO sys.path.appendで実装
os.environ["PATH"] += os.pathsep + str(resources.files("pokebot.Tesseract-OCR"))
os.environ["TESSDATA_PREFIX"] = str(resources.files("pokebot.Tesseract-OCR").joinpath("tessdata"))


OCR_LOG_DIR = Path(sys.argv[0]).resolve().parent / 'ocr_log'
CAP = None
NX, NXID = None, None


class Battle:
    def __init__(self, player1, player2, mode: BattleMode = BattleMode.SIM,
                 n_selection: int = 3, open_sheet: bool = False, max_turn: int = 999, seed: int = None,
                 video_id: int = 0, mute: bool = False):

        self.org_player = [player1, player2]
        self.mode = mode
        self.open_sheet = open_sheet if mode == BattleMode.SIM else False
        self.max_turn = max_turn
        self.seed = seed if seed is not None else int(time.time())
        self.mute = mute

        # プレイヤーに番号を割り振る
        for pidx in range(2):
            self.org_player[pidx].idx = pidx

        # 選出するポケモンの数を決める
        match self.mode:
            case BattleMode.SIM:
                # n_selectionかパーティ長のうち、少ないほう
                self.n_selection = min(n_selection, len(self.org_player[0].team), len(self.org_player[1].team))
            case BattleMode.OFFLINE:
                # パーティ全員
                self.n_selection = len(self.org_player[0].team)
            case BattleMode.ONLINE:
                # n_selection
                self.n_selection = n_selection

        # プレイヤーのコピーを作成
        self.player = deepcopy(self.org_player)

        # オープンシートなら情報を開示
        if self.open_sheet:
            for player in self.player:
                for p in player.team:
                    p.ability.observed = True
                    p.item.observed = True
                    for move in p.moves:
                        move.observed = True

        # 試合のリセット
        self.game_reset()

        # ポケモンの選出
        # オンライン戦ではmain_loop()内で行う
        for pidx, player in enumerate(self.player):
            match self.mode:
                case BattleMode.SIM:
                    # 方策関数に従う
                    self.phase = 'selection'
                    self.selection_indexes[pidx] = player.selection_command(self.masked(pidx))
                    self.phase = None
                case BattleMode.OFFLINE:
                    # 全員選出
                    self.selection_indexes[pidx] = list(range(len(self.player[0].team)))

        ''' TODO ダメージからBattle再現
        # 引数に指定があれば、ダメージ発生時の状況に上書きする
        if damage:
            self.pokemon = deepcopy(damage.pokemons)
            self.stellar[damage.attack_player_idx] = damage.stellar.copy()
            self.condition = deepcopy(damage.condition)
        '''

        # 対戦モードの初期化
        if self.mode != BattleMode.SIM:
            self.img = None                         # キャプチャ画像
            self.selection_command_time = 10        # 選出コマンドの入力にかかった時間 [s]
            self.battle_command_time = 10           # 対戦コマンドの入力にかかった時間 [s]
            self.switch_command_time = 3            # 交代コマンドの入力にかかった時間 [s]
            self.turn_start_time = None             # ターン開始時刻

            # キャプチャ設定
            global CAP
            print(f"{'-'*50}\nキャプチャデバイスを接続中 [video_id {video_id}] ...")
            print("\t'v4l2-ctl --list-devices' コマンドで確認可能\n")
            CAP = cv2.VideoCapture(video_id)
            CAP.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            CAP.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            CAP.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

            # nxbt macro controller設定
            import nxbt
            sys.modules['nxbt'] = nxbt

            global NX, NXID
            print('nxbtを接続中...')
            NX = nxbt.Nxbt()
            NXID = NX.create_controller(
                nxbt.PRO_CONTROLLER,
                reconnect_address=NX.get_switch_addresses(),
            )
            NX.wait_for_connection(NXID)
            print(f"{'-'*50}")

            # テンプレート画像の読み込み
            self.template_battle = ut.BGR2BIN(cv2.imread(
                ut.path_str("assets", "screen", "battle.png")), threshold=200, bitwise_not=True)
            self.template_switch = ut.BGR2BIN(cv2.imread(
                ut.path_str("assets", "screen", "switch.png")), threshold=150, bitwise_not=True)
            self.template_selection = ut.BGR2BIN(cv2.imread(
                ut.path_str("assets", "screen", "selection.png")), threshold=100, bitwise_not=True)
            self.template_standby = ut.BGR2BIN(cv2.imread(
                ut.path_str("assets", "screen", "standby.png")), threshold=100, bitwise_not=True)
            self.template_condition_window = ut.BGR2BIN(cv2.imread(
                ut.path_str("assets", "screen", "condition.png")), threshold=200, bitwise_not=True)
            self.template_fainting_symbol = ut.BGR2BIN(cv2.imread(
                ut.path_str("assets", "screen", "fainting_symbol.png")), threshold=128)

            self.template_alives = {}
            for s in ['alive', 'fainting', 'in_battle']:
                self.template_alives[s] = ut.BGR2BIN(cv2.imread(
                    ut.path_str("assets", "screen", f"{s}.png")), threshold=150, bitwise_not=True)

            self.template_winloss = {}
            for s in ['win', 'loss']:
                self.template_winloss[s] = ut.BGR2BIN(cv2.imread(
                    ut.path_str("assets", "screen", f"{s}.png")), threshold=140, bitwise_not=True)

            self.template_condition_turns = []
            for i in range(8):
                s = str(i+1)
                img = ut.BGR2BIN(cv2.imread(
                    ut.path_str("assets", "condition", "turn", f"{s}.png")), threshold=128)
                if cv2.countNonZero(img)/img.size < 0.5:
                    img = cv2.bitwise_not(img)
                self.template_condition_turns.append(img)

            self.template_condition_counts = []
            for i in range(3):
                s = str(i+1)
                img = ut.BGR2BIN(cv2.imread(
                    ut.path_str("assets", "condition", "count", f"{s}.png")), threshold=128)
                if cv2.countNonZero(img)/img.size < 0.5:
                    img = cv2.bitwise_not(img)
                self.template_condition_counts.append(img)

            self.template_condition_horobis = []
            for i in range(3):
                s = str(i+1)
                img = ut.BGR2BIN(cv2.imread(
                    ut.path_str("assets", "condition", "horobi", f"{s}.png")), threshold=128)
                if cv2.countNonZero(img)/img.size < 0.5:
                    img = cv2.bitwise_not(img)
                self.template_condition_counts.append(img)

            self.template_terastals = {}
            for t in PokeDB.type_file_code:
                img = ut.BGR2BIN(cv2.imread(
                    ut.path_str("assets", "terastal", f"{PokeDB.type_file_code[t]}.png")), threshold=230, bitwise_not=True)
                self.template_terastals[t] = img[24:-26, 20:-22]

            self.template_ailments = {}
            for s in PokeDB.ailments:
                self.template_ailments[s] = (ut.BGR2BIN(cv2.imread(
                    ut.path_str("assets", "screen", f"{s}.png")), threshold=200, bitwise_not=True))

            self.conditions = ['auroraveil'] + list(self.condition.keys()) + list(Pokemon().condition.keys())

            self.limited_conditions = ['aurora_veil'] + [
                'ame_mamire', 'encore', 'healblock', 'kanashibari', 'jigokuzuki', 'chohatsu', 'magnetrise', 'nemuke',
                'sunny', 'rainy', 'snow', 'sandstorm', 'elecfield', 'glassfield', 'psycofield', 'mistfield',
                'gravity', 'trickroom', 'oikaze', 'lightwall', 'reflector', 'safeguard', 'whitemist',
            ]

            self.countable_conditions = ['stock', 'makibishi', 'dokubishi']

            self.template_conditions = {}
            for s in self.conditions:
                img = ut.BGR2BIN(cv2.imread(
                    ut.path_str("assets", "condition", f"{s}.png")), threshold=128)
                if cv2.countNonZero(img)/img.size < 0.5:
                    img = cv2.bitwise_not(img)
                self.template_conditions[s] = img

    def game_reset(self):
        """試合開始前の状態に初期化する"""
        self.turn_reset()

        self.pokemon = [None] * 2                                   # 場のポケモン [Pokemon]
        self.selection_indexes = [[], []]                           # 選出されたポケモンの番号
        self.stellar = [PokeDB.types.copy() for _ in range(2)]      # ステラで強化できるタイプ

        self.condition = {
            'sunny': 0,             # はれ 残りターン
            'rainy': 0,             # あめ 残りターン
            'snow': 0,              # ゆき 残りターン
            'sandstorm': 0,         # すなあらし 残りターン
            'elecfield': 0,         # エレキフィールド 残りターン
            'glassfield': 0,        # グラスフィールド 残りターン
            'psycofield': 0,        # サイコフィールド 残りターン
            'mistfield': 0,         # ミストフィールド 残りターン
            'gravity': 0,           # じゅうりょく 残りターン
            'trickroom': 0,         # トリックルーム 残りターン

            'reflector': [0, 0],    # リフレクター 残りターン
            'lightwall': [0, 0],    # ひかりのかべ 残りターン
            'oikaze': [0, 0],       # おいかぜ 残りターン
            'safeguard': [0, 0],    # しんぴのまもり 残りターン
            'whitemist': [0, 0],    # しろいきり 残りターン
            'makibishi': [0, 0],    # まきびし カウント
            'dokubishi': [0, 0],    # どくびし カウント
            'stealthrock': [0, 0],  # ステルスロック
            'nebanet': [0, 0],      # ねばねばネット
            'wish': [0, 0],         # ねがいごと (残りターン)+0.001*(回復量)
        }

        self.turn = -1                                      # 現在のターン
        self._winner = None                                 # 勝者のプレイヤーインデックス
        self.breakpoint = [None, None]                      # ターン処理の追跡フラグ
        self.reserved_switches = [[], []]                   # 予約された交代
        self._random = random.Random(self.seed)             # 乱数生成器

        self.battle_log = BattleLogger()                    # 試合のログ
        self.damage_logs = []                               # ダメージ記録

        if self.mode != BattleMode.SIM:
            self.start_time = time.time()                   # 試合開始時刻
            self.text_buffer = []                           # 読み取った画面テキストを格納
            self.recognized_labels = []                     # 認識した情報のラベルを格納
            self.none_phase_start_time = 0                  # コマンド入力できないフェーズの開始時刻

    def turn_reset(self):
        """ターン開始時に初期化"""
        self.call_count = [0] * 2                           # 方策関数から呼ばれた回数
        self.move = [None] * 2                              # 発動した技
        self.move_succeeded = [True] * 2                    # 技が成功したらTrue
        self.damage_dealt = [0] * 2                         # 技で与えたダメージ。連続技なら最後のダメージ
        self.log = [[], []]                                 # ターン処理のログ
        self.command = [None] * 2                           # ターン行動のコマンド
        self.switch_history = [[], []]                      # 交代コマンドの履歴
        self.first_player_idx = 0                           # 先手のプレイヤーインデックス
        self.speed_order = [0, 1]                           # 素早さ順にプレイヤーインデックスを格納
        self._move_speed = [0] * 2                          # 発動した技の速度
        self.standby = [True] * 2                           # まだ行動していなければTrue
        self.already_switched = [False] * 2                 # すでに交代していたらTrue

        self._critical = False                              # 急所に当たったらTrue
        self._protect_move = None                           # 発動中のまもる系の技
        self._koraeru = False                               # こらえる状態ならTrue
        self._flinch = False                                # 相手をひるませたらTrue

    def mask(self, player_idx: int):
        """プレイヤー視点に相当するように非公開情報を隠蔽・補完する"""
        opp_idx = not player_idx

        # オープンシート制なら隠蔽しない
        if self.open_sheet:
            return

        # 方策関数の隠蔽
        self.player[opp_idx].selection_command = self.player[opp_idx].random_command
        self.player[opp_idx].battle_command = self.player[opp_idx].random_command
        self.player[opp_idx].switch_command = self.player[opp_idx].random_command

        # パーティの隠蔽
        for p in self.player[opp_idx].team:
            p.mask()

        # 選出の隠蔽
        self.selection_indexes[opp_idx] = \
            [i for i in self.selection_indexes[opp_idx] if self.player[opp_idx].team[i].observed]

        # 相手の選出を補完
        self.player[player_idx].complement_opponent_selection(self)

        # 相手が後手かつ未行動なら、相手が選択した技を補完
        if not self.standby[player_idx] and self.standby[opp_idx] and \
                not self.pokemon[opp_idx].unresponsive_turn:
            self.move[opp_idx] = self.player[player_idx].complement_opponent_move(self)

        # このターンに場の相手ポケモンが瀕死なら、相手の交代コマンドを補完
        if self.phase == 'switch' and self.pokemon[opp_idx].hp == 0:
            self.reserved_switches[opp_idx].append(
                self.player[player_idx].complement_opponent_switch(self))

    def masked(self, player_idx: int, called: bool = False) -> Battle:
        """非公開情報を隠蔽するしたコピーを返す"""
        battle = deepcopy(self)
        battle.mask(player_idx)
        if called:
            battle.call_count[player_idx] += 1
        return battle

    def dump(self) -> dict:
        # TODO Battle.dump()実装
        return {}

    def selected_pokemons(self, player_idx: int) -> list[Pokemon]:
        return [self.player[player_idx].team[i] for i in self.selection_indexes[player_idx]]

    ##################### ダメージ計算 #####################
    def lethal(self, atk_idx: int, move_list: list[str | Move], critical: bool = False,
               combo_hits: int = None, max_loop: int = 10) -> str:
        """
        致死率計算

        Parameters
        ----------
        atk_idx: int

        move_list: [str]
            攻撃技. 2個以上の場合は加算ダメージを計算

        critical: bool
            Trueなら急所

        combo_hits: int
            連続技の回数

        max_loop: int
            計算ループの上限回数

        Returns
        ----------
        str
            'd1~d2 (p1~p2 %) 確n' 形式の文字列.
        """

        def_idx = not atk_idx
        defender = self.pokemon[def_idx]

        # 単発ダメージ計算
        move_names, damage_dict_list = [], []

        # 加算計算
        for move in move_list:
            if type(move) is str:
                move = Move(move)

            critical |= move.name in PokeDB.move_category['critical']

            for i in range(self.num_strikes(atk_idx, move, n_default=combo_hits)):
                # 1ヒットあたりのダメージを計算
                r_power = i+1 if move.name == 'トリプルアクセル' else 1
                oneshot_damages = self.oneshot_damages(
                    atk_idx, move, lethal=True, critical=critical, power_scale=r_power)

                if not oneshot_damages:
                    break

                move_names.append(move.name)

                dict = {}
                for v in oneshot_damages:
                    ut.push(dict, str(v), 1)

                damage_dict_list.append(dict)

            # ターン終了フラグを追加
            move_names.append('END')
            damage_dict_list.append({})

        # 致死率計算
        self.damage_dict = {'0': 1}                     # 1ターン目に与えたダメージ
        self.hp_dict = {str(defender.hp): 1}            # 1ターン目終了時の残りHP
        self.lethal_num, self.lethal_prob = 0, 0

        if not move_names:
            return

        is_recoverable = defender.item.name in PokeDB.recovery_fruits and not self.is_nervous(def_idx)

        # {残りHP: 場合の数}
        hp_dict = {str(defender.hp)+('.0' if defender.item.active else ''): 1}

        # 瀕死になるまでターンを進める
        for i in range(max_loop):
            self.lethal_num += 1

            # 加算計算
            for (m, damage_dict) in zip(move_names, damage_dict_list):
                if m != 'END':
                    # ダメージ計算
                    move = Move(m)
                    new_hp_dict, new_damage_dict = {}, {}

                    for hp in hp_dict:
                        for dmg in damage_dict:
                            # ダメージ修正
                            d = int(dmg)
                            if float(hp) == defender.stats[0] and \
                                    self.get_defender_ability(def_idx, move) in ['ファントムガード', 'マルチスケイル']:
                                d = int(d/2)

                            # HPからダメージを引く
                            hp_key = str(int(max(0, float(hp)-d))) + '.0'*(hp[-2:] == '.0')

                            ut.push(new_hp_dict, hp_key, hp_dict[hp]*damage_dict[dmg])
                            ut.push(new_damage_dict, str(d), hp_dict[hp]*damage_dict[dmg])

                    hp_dict = new_hp_dict.copy()

                    # 回復実の判定
                    if is_recoverable:
                        hp_dict = defender.fruit_recovery(hp_dict)

                    # 1セット目のダメージを記録
                    if i == 0:
                        cross_sum = {}
                        for k1, v1 in self.damage_dict.items():
                            for k2, v2 in new_damage_dict.items():
                                cross_sum[str(int(k1)+int(k2))] = v1 * v2
                        self.damage_dict = cross_sum

                else:
                    # ターン終了時の処理
                    # 砂嵐ダメージ
                    if self.get_weather() == 'sandstorm' and not self.is_overcoat(def_idx) and \
                        all(s not in defender.types for s in ['いわ', 'じめん', 'はがね']) and \
                            defender.ability.name not in ['すなかき', 'すながくれ', 'すなのちから', 'マジックガード']:
                        hp_dict = ut.offset_hp_keys(hp_dict, -int(defender.stats[0]/16))
                        # 回復実の判定
                        if is_recoverable:
                            hp_dict = defender.fruit_recovery(hp_dict)

                    # 天候に関する特性
                    match self.get_weather(def_idx):
                        case 'sunny':
                            if defender.ability.name in ['かんそうはだ', 'サンパワー']:
                                hp_dict = ut.offset_hp_keys(hp_dict, -int(defender.stats[0]/8))
                                # 回復実の判定
                                if is_recoverable:
                                    hp_dict = defender.fruit_recovery(hp_dict)
                        case 'rainy':
                            match defender.ability.name:
                                case 'あめうけざら':
                                    hp_dict = ut.offset_hp_keys(hp_dict, int(defender.stats[0]/16))
                                case 'かんそうはだ':
                                    hp_dict = ut.offset_hp_keys(hp_dict, int(defender.stats[0]/8))
                        case 'snow':
                            if defender.ability == 'アイスボディ':
                                hp_dict = ut.offset_hp_keys(hp_dict, int(defender.stats[0]/16))

                    # グラスフィールド
                    if self.condition['glassfield'] and not self.is_float(def_idx):
                        hp_dict = ut.offset_hp_keys(hp_dict, int(defender.stats[0]/16))

                    # たべのこし系
                    match defender.item.name:
                        case 'たべのこし':
                            hp_dict = ut.offset_hp_keys(hp_dict, int(defender.stats[0]/16))
                        case 'くろいヘドロ':
                            r = 1 if 'どく' in defender.types else -1*(defender.ability != 'マジックガード')
                            hp_dict = ut.offset_hp_keys(hp_dict, int(defender.stats[0]/16*r))
                            if r == -1 and is_recoverable:
                                hp_dict = defender.fruit_recovery(hp_dict)  # 回復実の判定

                    # アクアリング・ねをはる
                    h = self.get_hp_drain(atk_idx, int(defender.stats[0]/16), from_opponent=False)
                    if defender.condition['aquaring']:
                        hp_dict = ut.offset_hp_keys(hp_dict, h)
                    if defender.condition['neoharu']:
                        hp_dict = ut.offset_hp_keys(hp_dict, h)

                    # やどりぎのタネ
                    if defender.condition['yadorigi'] and defender.ability != 'マジックガード':
                        hp_dict = ut.offset_hp_keys(hp_dict, -int(defender.stats[0]/16))
                        if is_recoverable:
                            hp_dict = defender.fruit_recovery(hp_dict)  # 回復実の判定

                    # 状態異常ダメージ
                    if defender.ability != 'マジックガード':
                        h = 0

                        match defender.ailment:
                            case 'PSN':
                                if defender.ability == 'ポイズンヒール':
                                    h = int(defender.stats[0]/8)
                                elif defender.condition['badpoison']:
                                    h = -int(defender.stats[0]/16 * defender.condition['badpoison'])
                                    defender.condition['badpoison'] += 1
                                else:
                                    h = -int(defender.stats[0]/8)
                            case 'BRN':
                                h = -int(defender.stats[0]/16)

                        if h:
                            hp_dict = ut.offset_hp_keys(hp_dict, h)
                            # 回復実の判定
                            if h < 0 and is_recoverable:
                                hp_dict = defender.fruit_recovery(hp_dict)

                    # 呪いダメージ
                    if defender.condition['noroi'] and defender.ability != 'マジックガード':
                        hp_dict = ut.offset_hp_keys(hp_dict, -int(defender.stats[0]/4))
                        # 回復実の判定
                        if is_recoverable:
                            hp_dict = defender.fruit_recovery(hp_dict)

                    # バインドダメージ
                    if defender.condition['bind'] and defender.ability != 'マジックガード':
                        hp_dict = ut.offset_hp_keys(
                            hp_dict, -int(defender.stats[0]/10/ut.frac(defender.condition['bind'])))
                        # 回復実の判定
                        if is_recoverable:
                            hp_dict = defender.fruit_recovery(hp_dict)

                    # しおづけダメージ
                    if defender.condition['shiozuke'] and defender.ability != 'マジックガード':
                        r = 2 if any(t in defender.types for t in ['みず', 'はがね']) else 1
                        hp_dict = ut.offset_hp_keys(hp_dict, -int(defender.stats[0]/8*r))
                        # 回復実の判定
                        if is_recoverable:
                            hp_dict = defender.fruit_recovery(hp_dict)

                    # 1ターン目のHPを記録
                    if i == 0:
                        self.hp_dict = hp_dict.copy()

                    # 致死率を計算
                    self.lethal_prob = ut.zero_ratio(hp_dict)

                    # 瀕死判定
                    if self.lethal_prob:
                        break

            # 瀕死判定
            if self.lethal_prob:
                break

        # "d1~d2 (p1~p2 %) 確n" の文字列を生成
        damages = [int(k) for k in list(self.damage_dict.keys())]
        Dmin, Dmax = min(damages), max(damages)

        result = f'{Dmin}~{Dmax} ({100*Dmin/defender.stats[0]:.1f}~{100*Dmax/defender.stats[0]:.1f}%)'
        if self.lethal_prob == 1:
            result += f' 確{self.lethal_num}'
        elif self.lethal_prob > 0:
            result += f' 乱{self.lethal_num}({100*self.lethal_prob:.2f}%)'

        return result

    def oneshot_damages(self, atk_idx: int, move: Move | str, critical: bool = False, power_scale: float = 1,
                        self_harm: bool = False, is_lethal: bool = False) -> list[int]:
        """
        技の1発あたりのダメージを返す

        Parameters
        ----------
        atk_idx: int

        move: Move

        critical: bool
            Trueなら急所

        power_scale: float
            任意の威力補正量. トリプルアクセルの計算に使用

        self_harm: bool
            Trueなら自傷

        is_lethal: bool
            致死率計算時のみTrue

        Returns
        ----------
        list[int]
            乱数ごとのダメージ
        """

        # ログの初期化
        self.damage_log = DamageLogger()

        if type(move) is str:
            move = Move(move)

        if move.power == 0:
            return []

        def_idx = not atk_idx if not self_harm else atk_idx
        attacker, defender = self.pokemon[atk_idx], self.pokemon[def_idx]

        self._critical = critical

        move_type = self.get_move_type(atk_idx, move)
        move_class = attacker.eff_move_class(move)

        # 補正値
        r_attack_type = self.attack_type_correction(atk_idx, move)
        r_defence_type = self.defence_type_correction(atk_idx, move, self_harm=self_harm)
        r_power = self.power_correction(atk_idx, move, self_harm=self_harm) * power_scale
        r_attack = self.attack_correction(atk_idx, move, self_harm=self_harm)
        r_defence = self.defence_correction(atk_idx, move, self_harm=self_harm)
        r_damage = self.damage_correction(atk_idx, move, self_harm=self_harm, is_lethal=is_lethal)
        # print(f"{move_type=}\n{r_attack_type=}\n{r_defence_type=}\n{r_power=}\n{r_attack=}\n{r_defence=}\n{r_damage=}")

        # 最終威力
        final_power = max(1, ut.round_half_down(move.power*r_power/4096))

        # 最終攻撃・ランク補正
        if move == 'ボディプレス':
            stat_idx = 2
        elif move_class == 'spe':
            stat_idx = 3
        else:
            stat_idx = 1

        atk_idx2 = def_idx if move == 'イカサマ' else atk_idx

        final_attack = self.pokemon[atk_idx2].stats[stat_idx]

        r_rank = self.pokemon[atk_idx2].rank_correction(stat_idx)

        if self.get_defender_ability(def_idx, move) == 'てんねん':
            if r_rank > 1:
                r_rank = 1
                self.damage_log[atk_idx].append('てんねん AC上昇無視')
        elif self._critical and r_rank < 1:
            r_rank = 1
            self.damage_log[atk_idx].append('急所 AC下降無視')

        final_attack = int(final_attack*r_rank)

        if attacker.ability == 'はりきり' and move_class == 'phy':
            final_attack = int(final_attack*1.5)
            self.damage_log[atk_idx].append('はりきり x1.5')

        final_attack = max(1, ut.round_half_down(final_attack*r_attack/4096))

        # 最終防御・ランク補正
        stat_idx = 2 if move_class == 'phy' or move.name in PokeDB.move_category['physical'] else 4
        final_defence = defender.stats[stat_idx]

        r_rank = 1 if move.name in PokeDB.move_category['ignore_rank'] else \
            defender.rank_correction(stat_idx)

        if self.get_defender_ability(atk_idx, move) == 'てんねん':
            if r_rank > 1:
                r_rank = 1
                self.damage_log[atk_idx].append('てんねん BD上昇無視')
        elif self._critical and r_rank > 1:
            r_rank = 1
            self.damage_log[atk_idx].append('急所 BD上昇無視')

        final_defence = int(final_defence*r_rank)

        # 雪・砂嵐補正
        if self.get_weather() == 'snow' and 'こおり' in defender.types and move_class == 'phy':
            final_defence = int(final_defence*1.5)
            self.damage_log[atk_idx].append('ゆき 防御 x1.5')
        elif self.get_weather() == 'sandstorm' and 'いわ' in defender.types and move_class == 'spe':
            final_defence = int(final_defence*1.5)
            self.damage_log[atk_idx].append('すなあらし 特防 x1.5')

        final_defence = max(1, ut.round_half_down(final_defence*r_defence/4096))

        # 最大乱数ダメージ
        max_damage = int(int(int(attacker.level*0.4+2)*final_power*final_attack/final_defence)/50+2)

        # 晴・雨補正
        if self.get_weather(def_idx) == 'sunny':
            match move_type:
                case 'ほのお':
                    max_damage = ut.round_half_down(max_damage*1.5)
                    self.damage_log[atk_idx].append('はれ x1.5')
                case 'みず':
                    max_damage = ut.round_half_down(max_damage*0.5)
                    self.damage_log[atk_idx].append('はれ x0.5')

        elif self.get_weather(def_idx) == 'rainy':
            match move_type:
                case 'ほのお':
                    max_damage = ut.round_half_down(max_damage*0.5)
                    self.damage_log[atk_idx].append('あめ x0.5')
                case 'みず':
                    max_damage = ut.round_half_down(max_damage*1.5)
                    self.damage_log[atk_idx].append('あめ x1.5')

        if defender.executed_move == 'きょけんとつげき' and def_idx == self.first_player_idx:
            max_damage = ut.round_half_down(max_damage*2)
            self.damage_log[atk_idx].append('きょけんとつげき x2.0')

        # 急所
        if self._critical:
            max_damage = ut.round_half_down(max_damage*1.5)
            self.damage_log[atk_idx].append('急所 x1.5')

        damages = [0]*16

        for i in range(16):
            # 乱数 85~100%
            damages[i] = int(max_damage*(0.85+0.01*i))

            # 攻撃タイプ補正
            damages[i] = ut.round_half_down(damages[i]*r_attack_type)

            # 防御タイプ補正
            damages[i] = int(damages[i]*r_defence_type)

            # 状態異常補正
            if attacker.ailment == 'BRN' and move_class == 'phy' and \
                    attacker.ability != 'こんじょう' and move != 'からげんき':
                damages[i] = ut.round_half_down(damages[i]*0.5)
                if i == 0:
                    self.damage_log[atk_idx].append('やけど x0.5')

            # ダメージ補正
            damages[i] = ut.round_half_down(damages[i]*r_damage/4096)

            # 最低ダメージ補償
            if damages[i] == 0 and r_defence_type*r_damage > 0:
                damages[i] = 1

        return damages

    def num_strikes(self, atk_idx: int, move: Move, n_default: int = None) -> int:
        """技の発動回数"""
        if move.name not in PokeDB.move_combo:
            return 1

        attacker = self.pokemon[atk_idx]
        n_min, n_max = PokeDB.move_combo[move.name]

        if n_default and n_min <= n_default <= n_max:
            return n_default

        if n_min != n_max:
            if attacker.ability == 'スキルリンク':
                return n_max
            elif attacker.item == 'いかさまダイス':
                return n_max - self._random.randint(0, 1)
            elif n_min == 2 and n_max == 5:
                return self._random.choice([2, 2, 2, 3, 3, 3, 4, 5])

        return n_max

    def attack_type_correction(self, atk_idx: int, move: Move) -> float:
        """攻撃タイプ補正値"""
        attacker = self.pokemon[atk_idx]
        move_type = self.get_move_type(atk_idx, move)
        r = 1

        if attacker.terastal and move != 'テラバースト':
            r0 = r
            if attacker.terastal == 'ステラ' and move_type in self.stellar[atk_idx]:
                if move_type in attacker.org_types:
                    r = r*2.25 if attacker.ability == 'てきおうりょく' else r*2.0
                else:
                    r *= 1.2
                self.damage_log[atk_idx].append(f'{attacker.terastal}T x{r/r0:.1f}')

            elif move_type == attacker.terastal:
                if attacker.terastal in attacker.org_types:
                    r = r*2.25 if attacker.ability == 'てきおうりょく' else r*2.0
                else:
                    r = r*2 if attacker.ability == 'てきおうりょく' else r*1.5
                self.damage_log[atk_idx].append(f'{attacker.terastal}T x{r/r0:.1f}')

            elif move_type in attacker.org_types:
                r *= 1.5

        else:
            if move_type in attacker.types:
                r = r*2 if attacker.ability == 'てきおうりょく' else r*1.5

        return r

    def defence_type_correction(self, atk_idx: int, move: Move, self_harm: bool = False) -> float:
        """防御タイプ補正値。{self_harm}=Trueなら自傷"""
        def_idx = not atk_idx if not self_harm else atk_idx

        attacker, defender = self.pokemon[atk_idx], self.pokemon[def_idx]
        move_type = self.get_move_type(atk_idx, move)

        r = 1

        if move_type == 'ステラ' and defender.terastal:
            r = 2
        else:
            for t in defender.types:
                if attacker.ability.name in ['しんがん', 'きもったま'] and t == 'ゴースト' and move_type in ['ノーマル', 'かくとう']:
                    self.damage_log[atk_idx].append(attacker.ability.name)
                elif move == 'フリーズドライ' and t == 'みず':
                    r *= 2
                elif not self.is_float(def_idx) and move_type == 'じめん' and t == 'ひこう':
                    continue
                else:
                    r *= PokeDB.type_correction[move_type][t]
                    if move == 'フライングプレス':
                        r *= PokeDB.type_correction['ひこう'][t]
                    if r == 0:
                        if defender.item == 'ねらいのまと':
                            r = 1
                        else:
                            break

        if (def_ability := self.get_defender_ability(def_idx, move)) == 'テラスシェル' and \
                r and defender.hp_ratio == 1:
            r = 0.5
            self.damage_log[atk_idx].append(f'{def_ability} x{r:.1f}')

        return r

    def power_correction(self, atk_idx: int, move: Move, self_harm: bool = False) -> float:
        """威力補正値。{self_harm}=Trueなら自傷"""
        def_idx = not atk_idx if not self_harm else atk_idx
        attacker, defender = self.pokemon[atk_idx], self.pokemon[def_idx]
        selected_attackers = self.selected_pokemons(atk_idx)

        move_type = self.get_move_type(atk_idx, move)
        move_class = attacker.eff_move_class(move)

        r = 4096

        # 攻撃側
        if 'オーガポン(' in attacker.name:
            r = ut.round_half_up(r*4915/4096)
            self.damage_log[atk_idx].append('おめん x1.2')

        # 威力変動技
        r0 = r
        match move.name:
            case 'アクロバット':
                if attacker.item.name:
                    r = ut.round_half_up(r*2)
            case 'アシストパワー' | 'つけあがる':
                r = ut.round_half_up(
                    r*(1 + sum(v for v in attacker.rank[1:] if v >= 0)))
            case 'ウェザーボール':
                if self.get_weather(atk_idx):
                    r = ut.round_half_up(r*2)
            case 'エレキボール':
                x = self.get_speed(atk_idx)/self.get_speed(def_idx)
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
                r *= (1 + sum(1 for p in selected_attackers if p.hp == 0))
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
                if atk_idx != self.first_player_idx:
                    r = ut.round_half_up(r*2)
            case 'ジャイロボール':
                r = ut.round_half_up(
                    r*min(150, int(1+25*self.get_speed(def_idx)/self.get_speed(atk_idx))))
            case 'Gのちから':
                if self.condition['gravity']:
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
                p0 = 120 if move == 'にぎりつぶす' else 100
                r *= ut.round_half_down(p0 * defender.hp_ratio)
            case 'はたきおとす':
                if not defender.item.name:
                    r = ut.round_half_up(r*1.5)
            case 'ふんどのこぶし':
                r *= (1 + attacker.hits_taken)
            case 'ベノムショック':
                if defender.ailment == 'PSN':
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
                if atk_idx != self.first_player_idx and self.damage_dealt[def_idx]:
                    r = ut.round_half_up(r*2)

        # 変動があればログに記録
        if r0 != r:
            self.damage_log[atk_idx].append(f'{move} x{r/r0:.1f}')

        if attacker.ability == 'テクニシャン' and move.power*r/4096 <= 60:
            r = ut.round_half_up(r*1.5)
            self.damage_log[atk_idx].append(f'{attacker.ability} x1.5')

        # 以降の技はテクニシャン非適用
        if move.name in ['ソーラービーム', 'ソーラーブレード']:
            rate = 0.5 if self.get_weather() == 'sandstorm' else 1
            r = ut.round_half_up(r*rate)
            if rate != 1:
                self.damage_log[atk_idx].append(f'{move} x{rate}')

        r0 = r
        match attacker.ability.name:
            case 'アナライズ':
                if atk_idx != self.first_player_idx:
                    r = ut.round_half_up(r*5325/4096)
            case 'エレキスキン':
                if move.type == 'ノーマル':
                    r = ut.round_half_up(r*4915/4096)
            case 'かたいつめ':
                if move.name in PokeDB.move_category['contact']:
                    r = ut.round_half_up(r*5325/4096)
            case 'がんじょうあご':
                if move.name in PokeDB.move_category['bite']:
                    r = ut.round_half_up(r*1.5)
            case 'きれあじ':
                if move.name in PokeDB.move_category['slash']:
                    r = ut.round_half_up(r*1.5)
            case 'スカイスキン':
                if move.type == 'ノーマル':
                    r = ut.round_half_up(r*4915/4096)
            case 'すてみ':
                if move.name in PokeDB.move_value['recoil'] or move.name in PokeDB.move_value['mis_recoil']:
                    r = ut.round_half_up(r*4915/4096)
            case 'すなのちから':
                if self.get_weather() == 'sandstorm' and move_type in ['いわ', 'じめん', 'はがね']:
                    r = ut.round_half_up(r*5325/4096)
            case 'そうだいしょう':
                ls = [4096, 4506, 4915, 5325, 5734, 6144]
                n = sum(p.hp == 0 for p in selected_attackers)
                r = ut.round_half_up(r*ls[n]/4096)
            case 'ダークオーラ' | 'フェアリーオーラ':
                if (attacker.ability == 'ダークオーラ' and move_type == 'あく') or \
                        (attacker.ability == 'フェアリーオーラ' and move_type == 'フェアリー'):
                    v = 5448/4096
                    if defender.ability == 'オーラブレイク':
                        v = 1/v
                    r = ut.round_half_up(r*v)
            case 'ちからずく':
                if move.name in PokeDB.move_effect:
                    r = ut.round_half_up(r*5325/4096)
            case 'てつのこぶし':
                if move.name in PokeDB.move_category['punch']:
                    r = ut.round_half_up(r*4915/4096)
            case 'とうそうしん':
                match attacker.gender.value * defender.gender.value:
                    case 1:
                        r = ut.round_half_up(r*1.25)
                    case -1:
                        r = ut.round_half_up(r*5072/4096)
            case 'どくぼうそう':
                if attacker.ailment == 'PSN' and move_class == 'phy':
                    r = ut.round_half_up(r*1.5)
            case 'ノーマルスキン':
                if move != 'わるあがき' and move.type != 'ノーマル':
                    r = ut.round_half_up(r*4915/4096)
            case 'パンクロック':
                if move.name in PokeDB.move_category['sound']:
                    r = ut.round_half_up(r*5325/4096)
            case 'フェアリースキン':
                if move.type == 'ノーマル':
                    r = ut.round_half_up(r*4915/4096)
            case 'フリーズスキン':
                if move.type == 'ノーマル':
                    r = ut.round_half_up(r*4915/4096)
            case 'メガランチャー':
                if move.name in PokeDB.move_category['wave']:
                    r = ut.round_half_up(r*1.5)

        # 変動があればログに記録
        if r != r0:
            self.damage_log[atk_idx].append(f'{attacker.ability} x{r/r0:.1f}')

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
                if move_class == 'phy':
                    r = ut.round_half_up(r*4505/4096)
            case 'ノーマルジュエル':
                if move_type == 'ノーマル':
                    r = ut.round_half_up(r*5325/4096)
                    self.damage_log[atk_idx].append(attacker.item.name)  # アイテム消費判定用
            case 'パンチグローブ':
                if move.name in PokeDB.move_category['punch']:
                    r = ut.round_half_up(r*4506/4096)
            case 'ものしりメガネ':
                if move_class == 'spe':
                    r = ut.round_half_up(r*4505/4096)
            case _:
                if move_type == attacker.item.buff_type:
                    r = ut.round_half_up(r*4915/4096)

        # 変動があればログに記録
        if r != r0:
            self.damage_log[atk_idx].append(f'{attacker.item} x{r/r0:.1f}')

        # フィールド補正
        r0 = r
        if self.condition['elecfield']:
            if move_type == 'でんき' and not self.is_float(atk_idx):
                r = ut.round_half_up(r*5325/4096)
            if move == 'ライジングボルト' and not self.is_float(def_idx):
                r = ut.round_half_up(r*2)

        elif self.condition['glassfield']:
            if move_type == 'くさ' and not self.is_float(atk_idx):
                r = ut.round_half_up(r*5325/4096)
            if move.name in ['じしん', 'じならし', 'マグニチュード'] and not self.is_float(def_idx):
                r = ut.round_half_up(r*0.5)

        elif self.condition['psycofield']:
            if move_type == 'エスパー' and not self.is_float(atk_idx):
                r = ut.round_half_up(r*5325/4096)
            if move == 'ワイドフォース' and not self.is_float(def_idx):
                r = ut.round_half_up(r*1.5)

        elif self.condition['mistfield']:
            if move_type == 'ドラゴン' and not self.is_float(def_idx):
                r = ut.round_half_up(r*0.5)
            if move == 'ミストバースト' and not self.is_float(atk_idx):
                r = ut.round_half_up(r*1.5)

        # 変動があればログに記録
        if r != r0:
            self.damage_log[atk_idx].append(f'フィールド x{r/r0:.1f}')

        # 防御側の特性
        r0 = r
        match self.get_defender_ability(def_idx, move).name:
            case 'かんそうはだ':
                if move_type == 'ほのお':
                    r = ut.round_half_up(r*1.25)
                elif move_type == 'みず':
                    r = 0
                    self.damage_log[atk_idx].append(defender.ability.name)  # 特性発動判定用

            case 'たいねつ':
                if move_type == 'ほのお':
                    r = ut.round_half_up(r*0.5)

        # 変動があればログに記録
        if r != r0:
            self.damage_log[atk_idx].append(f'{defender.ability} x{r/r0:.1f}')

        return r

    def attack_correction(self, atk_idx: int, move: Move, self_harm: bool = False) -> float:
        """攻撃補正値。{self_harm}=Trueなら自傷"""
        def_idx = not atk_idx if not self_harm else atk_idx
        attacker, defender = self.pokemon[atk_idx], self.pokemon[def_idx]

        move_type = self.get_move_type(atk_idx, move)
        move_class = attacker.eff_move_class(move)

        r = 4096

        # 攻撃側
        if f"{move_class}{attacker.boosted_idx}" in ['phy1', 'spe3']:
            r = ut.round_half_up(r*5325/4096)
            self.damage_log[atk_idx].append('ACブースト x1.3')

        r0 = r
        match attacker.ability.name:
            case 'いわはこび':
                if move_type == 'いわ':
                    r = ut.round_half_up(r*1.5)
            case 'げきりゅう':
                if move_type == 'みず' and attacker.hp_ratio <= 1/3:
                    r = ut.round_half_up(r*1.5)
            case 'ごりむちゅう':
                if move_class == 'phy':
                    r = ut.round_half_up(r*1.5)
            case 'こんじょう':
                if attacker.ailment and move_class == 'phy':
                    r = ut.round_half_up(r*1.5)
            case 'サンパワー':
                if self.get_weather() == 'sunny' and move_class == 'spe':
                    r = ut.round_half_up(r*1.5)
            case 'しんりょく':
                if move_type == 'くさ' and attacker.hp_ratio <= 1/3:
                    r = ut.round_half_up(r*1.5)
            case 'すいほう':
                if move_type == 'みず':
                    r = r = ut.round_half_up(r*2)
            case 'スロースタート':
                r = ut.round_half_up(r*0.5)
            case 'ちからもち' | 'ヨガパワー':
                if move_class == 'phy':
                    r = ut.round_half_up(r*2)
            case 'トランジスタ':
                if move_type == 'でんき':
                    r = ut.round_half_up(r*1.3)
            case 'ねつぼうそう':
                if attacker.ailment == 'BRN' and move_class == 'spe':
                    r = ut.round_half_up(r*1.5)
            case 'はがねつかい' | 'はがねのせいしん':
                if move_type == 'はがね':
                    r = ut.round_half_up(r*1.5)
            case 'ハドロンエンジン':
                if self.condition['elecfield']:
                    r = ut.round_half_up(r*5461/4096)
            case 'はりこみ':
                if self.already_switched[def_idx]:
                    r = ut.round_half_up(r*2)
            case 'ひひいろのこどう':
                if self.get_weather() == 'sunny':
                    r = ut.round_half_up(r*5461/4096)
            case 'フラワーギフト':
                if self.get_weather() == 'sunny':
                    r = ut.round_half_up(r*1.5)
            case 'むしのしらせ':
                if move_type == 'むし' and attacker.hp_ratio <= 1/3:
                    r = ut.round_half_up(r*1.5)
            case 'もうか':
                if move_type == 'ほのお' and attacker.hp_ratio <= 1/3:
                    r = ut.round_half_up(r*1.5)
            case 'よわき':
                if attacker.hp_ratio <= 1/2:
                    r = ut.round_half_up(r*0.5)
            case 'りゅうのあぎと':
                if move_type == 'ドラゴン':
                    r = ut.round_half_up(r*1.5)

        # 変動があればログに記録
        if r != r0:
            self.damage_log[atk_idx].append(f'{attacker.ability} x{r/r0:.1f}')

        if attacker.ability == 'もらいび' and attacker.ability.count and move_type == 'ほのお':
            r = ut.round_half_up(r*1.5)
            attacker.ability.count = 0
            self.damage_log[atk_idx].append(f'もらいび x1.5')

        r0 = r
        match attacker.item.name:
            case 'こだわりハチマキ':
                if move_class == 'phy':
                    r = ut.round_half_up(r*1.5)
            case 'こだわりメガネ':
                if move_class == 'spe':
                    r = ut.round_half_up(r*1.5)
            case 'でんきだま':
                if attacker.name == 'ピカチュウ':
                    r = ut.round_half_up(r*2)

        # 変動があればログに記録
        if r != r0:
            self.damage_log[atk_idx].append(f'{attacker.item} x{r/r0:.1f}')

        # 防御側
        r0 = r
        match self.get_defender_ability(def_idx, move).name:
            case 'あついしぼう':
                if move_type in ['ほのお', 'こおり']:
                    r = ut.round_half_up(r*0.5)
            case 'きよめのしお':
                if move_type == 'ゴースト':
                    r = ut.round_half_up(r*0.5)
            case 'わざわいのうつわ':
                if move_class == 'spe':
                    r = ut.round_half_up(r*5072/4096)
            case 'わざわいのおふだ':
                if move_class == 'phy':
                    r = ut.round_half_up(r*5072/4096)

        if r != r0:
            self.damage_log[atk_idx].append(f'{defender.ability} x{r/r0:.2f}')

        return r

    def defence_correction(self, atk_idx: int, move: Move, self_harm: bool = False) -> float:
        """防御補正値。{self_harm}=Trueなら自傷"""
        def_idx = not atk_idx if not self_harm else atk_idx
        attacker, defender = self.pokemon[atk_idx], self.pokemon[def_idx]

        move_type = self.get_move_type(atk_idx, move)
        move_class = attacker.eff_move_class(move)

        r = 4096

        # 攻撃側
        r0 = r
        match attacker.ability.name:
            case 'わざわいのたま':
                if move_class == 'spe' and move.name not in PokeDB.move_category['physical']:
                    r = ut.round_half_up(r*5072/4096)
            case 'わざわいのつるぎ':
                if move_class == 'phy' or move.name in PokeDB.move_category['physical']:
                    r = ut.round_half_up(r*5072/4096)

        # 変動があればログに記録
        if r != r0:
            self.damage_log[atk_idx].append(f'{attacker.ability} x{r0/r:.2f}')

        # 防御側
        if ((move_class == 'phy' or move.name in PokeDB.move_category['physical']) and defender.boosted_idx == 2) or \
                (move_class == 'spe' and move.name not in PokeDB.move_category['physical'] and defender.boosted_idx == 4):
            r = ut.round_half_up(r*5325/4096)
            self.damage_log[atk_idx].append('BDブースト x0.77')

        r0 = r
        match defender.item.name:
            case 'しんかのきせき':
                if True:
                    r = ut.round_half_up(r*1.5)
            case 'とつげきチョッキ':
                if move_class == 'spe' and move.name not in PokeDB.move_category['physical']:
                    r = ut.round_half_up(r*1.5)

        # 変動があればログに記録
        if r != r0:
            self.damage_log[atk_idx].append(f'{defender.item} x{r0/r:.2f}')

        r0 = r
        match self.get_defender_ability(def_idx, move).name:
            case 'くさのけがわ':
                if self.condition['glassfield'] and (move_class == 'phy' or move.name in PokeDB.move_category['physical']):
                    r = ut.round_half_up(r*1.5)
            case 'すいほう':
                if move_type == 'ほのお':
                    r = ut.round_half_up(r*2)
            case 'ファーコート':
                if move_class == 'phy' or move.name in PokeDB.move_category['physical']:
                    r = ut.round_half_up(r*2)
            case 'ふしぎなうろこ':
                if defender.ailment and (move_class == 'phy' or move.name in PokeDB.move_category['physical']):
                    r = ut.round_half_up(r*1.5)
            case 'フラワーギフト':
                if self.get_weather() == 'sunny':
                    r = ut.round_half_up(r*1.5)

        # 変動があればログに記録
        if r != r0:
            self.damage_log[atk_idx].append(f'{defender.ability} x{r0/r:.2f}')

        return r

    def damage_correction(self, atk_idx: int, move: Move, self_harm: bool = False,
                          is_lethal: bool = False) -> float:
        """ダメージ補正値。{self_harm}=Trueなら自傷"""
        def_idx = not atk_idx if not self_harm else atk_idx
        attacker, defender = self.pokemon[atk_idx], self.pokemon[def_idx]

        move_type = self.get_move_type(atk_idx, move)
        move_class = attacker.eff_move_class(move)

        r = 4096
        r_defence_type = self.defence_type_correction(atk_idx, move)

        r0 = r
        match move.name:
            case 'アクセルブレイク' | 'イナズマドライブ':
                if r_defence_type > 1:
                    r = ut.round_half_up(r*5461/4096)
            case 'じしん' | 'マグニチュード':
                if defender.hidden and defender.executed_move == 'あなをほる':
                    r *= 2
            case 'なみのり':
                if defender.hidden and defender.executed_move == 'ダイビング':
                    r *= 2

        # 変動があればログに記録
        if r != r0:
            self.damage_log[atk_idx].append(f'{move} x{r/r0:.2f}')

        # 攻撃側の特性
        match attacker.ability.name:
            case 'いろめがね':
                if r_defence_type < 1:
                    r *= 2
                    self.damage_log[atk_idx].append(f'{attacker.ability} x2')
            case 'スナイパー':
                if self._critical:
                    r = ut.round_half_up(r*1.5)
                    self.damage_log[atk_idx].append('スナイパー x1.5')

        # 防御側の特性
        r0 = r
        match self.get_defender_ability(def_idx, move).name:
            case 'かぜのり':
                if move.name in PokeDB.move_category['wind']:
                    r = 0
                    self.damage_log[atk_idx].append(defender.ability.name)  # 特性発動判定用
            case 'こおりのりんぷん':
                if move_class == 'spe':
                    r = ut.round_half_up(r*0.5)
            case 'こんがりボディ':
                if move_type == 'ほのお':
                    r = 0
                    self.damage_log[atk_idx].append(defender.ability.name)  # 特性発動判定用
            case 'そうしょく':
                if move_type == 'くさ':
                    r = 0
                    self.damage_log[atk_idx].append(defender.ability.name)  # 特性発動判定用
            case 'ちくでん' | 'でんきエンジン' | 'ひらいしん':
                if move_type == 'でんき':
                    r = 0
                    self.damage_log[atk_idx].append(defender.ability.name)  # 特性発動判定用
            case 'ちょすい' | 'よびみず':
                if move_type == 'みず':
                    r = 0
                    self.damage_log[atk_idx].append(defender.ability.name)  # 特性発動判定用
            case 'どしょく':
                if move_type == 'じめん':
                    r = 0
                    self.damage_log[atk_idx].append(defender.ability.name)  # 特性発動判定用
            case 'ハードロック':
                if self.defence_type_correction(atk_idx, move) > 1:
                    r = ut.round_half_up(r*0.75)
            case 'パンクロック':
                if move.name in PokeDB.move_category['sound']:
                    r = ut.round_half_up(r*0.5)
            case 'フィルター' | 'プリズムアーマー':
                if self.defence_type_correction(atk_idx, move) > 1:
                    r = ut.round_half_up(r*5072/4096)
            case 'ぼうおん':
                if move.name in PokeDB.move_category['sound']:
                    r = 0
            case 'ぼうだん':
                if move.name in PokeDB.move_category['bullet']:
                    r = 0
            case 'ファントムガード' | 'マルチスケイル':
                if not is_lethal and defender.hp_ratio == 1:
                    r = ut.round_half_up(r*0.5)
            case 'もふもふ':
                if move_type == 'ほのお':
                    r = ut.round_half_up(r*2)
                elif move.name in PokeDB.move_category['contact']:
                    r = ut.round_half_up(r*0.5)

        # 変動があればログに記録
        if r != r0:
            self.damage_log[atk_idx].append(f'{defender.ability} x{r/r0:.2f}')

        if self.get_defender_ability(def_idx, move) == 'もらいび' and move_type == 'ほのお':
            r = 0
            self.damage_log[atk_idx].append('もらいび x0.0')
            self.damage_log[atk_idx].append('もらいび')  # 特性の発動判定のために一時記録

        # 攻撃側のアイテム
        r0 = r
        match attacker.item.name:
            case 'いのちのたま':
                r = ut.round_half_up(r*5324/4096)
            case 'たつじんのおび':
                if r_defence_type > 1:
                    r = ut.round_half_up(r*4915/4096)

        # 変動があればログに記録
        if r != r0:
            self.damage_log[atk_idx].append(f'{attacker.item} x{r/r0:.1f}')

        # 壁
        if not self._critical and attacker.ability != 'すりぬけ' and move.name not in PokeDB.move_category['wall_break']:
            if self.condition['reflector'][def_idx] and move_class == 'phy':
                r = ut.round_half_up(r*0.5)
                self.damage_log[atk_idx].append('リフレクター x0.5')

            if self.condition['lightwall'][def_idx] and move_class == 'spe':
                r = ut.round_half_up(r*0.5)
                self.damage_log[atk_idx].append('ひかりのかべ x0.5')

        # 粉技無効
        if move.name in PokeDB.move_category['powder']:
            if self.is_overcoat(def_idx, move):
                r = 0
                self.damage_log[atk_idx].append('ぼうじん')
            elif move != 'わたほうし' and 'くさ' in defender.types:
                r = 0
                self.damage_log[atk_idx].append('粉わざ x0.0')

        if move_type == 'じめん' and self.is_float(def_idx):
            r = 0
            self.damage_log[atk_idx].append('浮遊 x0.0')

        # 半減実
        r0 = r
        if defender.item.debuff_type == move_type and not self.is_nervous(def_idx):
            if move_type == 'ノーマル' or r_defence_type > 1:
                r = ut.round_half_up(r*0.5)

        # 変動があればログに記録
        if r != r0:
            self.damage_log[atk_idx].append(f'{defender.item} x{r/r0:.1f}')
            self.damage_log[def_idx].append(defender.item.name)  # アイテム消費判定用

        return r

    ##################### 対戦シミュレーション #####################
    def proceed_turn(self, commands: list[int] = [None]*2, switch_commands: list[int] = [None]*2):
        """1ターン進める

        Parameters
        ----------
        commands: [int]
            ターン開始時に入力するコマンド
            Noneなら方策関数を参照する

        switch_commands: [int]
            自由交代時に入力するコマンド
            Noneなら方策関数を参照する
        """

        # 対戦の設定を記録
        if 'mode' not in self.game_log:
            self.game_log['mode'] = self.mode.value
            self.game_log['n_selection'] = self.n_selection
            self.game_log['seed'] = self.seed

            for pidx in range(2):
                self.game_log[f"team_{pidx}"] = [p.dump() for p in self.player[pidx].team]
                self.game_log[f"selection_indexes_{pidx}"] = self.selection_indexes[pidx]

        # ターンの初期化
        if not any(self.breakpoint):
            self.turn_reset()
            self.turn += 1

        if self.turn == 0:
            # 0ターン目は先頭のポケモンを場に出して終了
            if not any(self.breakpoint):
                # 交代
                for pidx in range(2):
                    self.switch_pokemon(pidx, idx=self.selection_indexes[pidx][0], landing=False)

                # 着地処理 (両者が場に出た後に行う)
                for pidx in self.speed_order:
                    self.land(pidx)

                # だっしゅつパック判定 (0ターン目)
                if (pidxs := [pidx for pidx in self.speed_order if self.is_ejectpack_triggered(pidx)]):
                    self.breakpoint[pidxs[0]] = 'ejectpack_turn0'
                    self.pokemon[pidxs[0]].item.consume()
                    for pidx in pidxs:
                        self.pokemon[pidx].rank_dropped = False

            # だっしゅつパックによる交代
            if (s := 'ejectpack_turn0') in self.breakpoint:
                pidx = self.breakpoint.index(s)
                self.switch_pokemon(pidx, command=switch_commands[pidx])
                # コマンド破棄
                switch_commands[pidx] = None

            # このターンに入力されたコマンドを記録
            self.record_command()

            return

        if not any(self.breakpoint):
            # 行動コマンドを取得
            for pidx in range(2):
                if commands[pidx] is None:
                    # 方策関数に従う
                    self.phase = 'battle'
                    self.command[pidx] = self.player[pidx].battle_command(self.masked(pidx, called=True))
                    self.phase = None
                else:
                    # 引数のコマンドを使う
                    self.command[pidx] = commands[pidx]

                self.log[pidx].append(self.pokemon[pidx].name)
                if self.pokemon[pidx].terastal:
                    self.log[pidx][-1] += f"_{self.pokemon[pidx].terastal}T"
                self.log[pidx].append(f'HP {self.pokemon[pidx].hp}/{self.pokemon[pidx].stats[0]}')
                self.log[pidx].append(f'コマンド {self.command[pidx]}')

            # 素早さ順を更新
            self.update_speed_order()

            # 行動順を更新
            self.update_action_order()

            # 相手の素早さを推定
            for pidx in range(2):
                self.estimate_opponent_speed(pidx)

        for pidx in range(2):
            # 交代
            if not any(self.breakpoint) and self.command[pidx] in CommandRange['switch']:
                self.switch_pokemon(pidx, command=self.command[pidx])

                # だっしゅつパック判定 (交代後)
                if (pidxs := [i for i in self.speed_order if self.is_ejectpack_triggered(i)]):
                    self.breakpoint[pidxs[0]] = f'ejectpack_switch_{pidx}'
                    self.pokemon[pidxs[0]].item.consume()
                    for i in pidxs:
                        self.pokemon[i].rank_dropped = False

            # だっしゅつパックによる交代
            if (s := f'ejectpack_switch_{pidx}') in self.breakpoint:
                idx = self.breakpoint.index(s)
                self.switch_pokemon(idx, command=switch_commands[idx])
                switch_commands[idx] = None  # コマンド破棄

        if not any(self.breakpoint):
            for pidx in range(2):
                if self.command[pidx] in CommandRange['terastal']:
                    # テラスタル発動
                    self.pokemon[pidx].terastal = True
                    self.log[pidx].append(f'テラスタル {self.pokemon[pidx].terastal}')

                    # 特性発動
                    if self.pokemon[pidx].ability.name in ['おもかげやどし', 'ゼロフォーミング']:
                        self.activate_ability(pidx)

        # 行動処理
        for pidx in self.action_order:
            move = self.move[pidx]
            move_class = self.pokemon[pidx].eff_move_class(move) if move else None

            if not any(self.breakpoint):
                self.standby[pidx] = False

                # 行動スキップ (特殊コマンド)
                if self.command[pidx] == Command.SKIP:
                    self.log[pidx].append('行動スキップ')
                    self.pokemon[pidx].no_act()
                    continue

                # このターンに交代していたら行動しない
                if self.already_switched[pidx]:
                    # self.log[pidx].append('行動不能 交代')
                    continue

                # みちづれ/おんねん解除
                self.pokemon[pidx].condition['michizure'] = 0

                # 反動
                if not move:
                    self.log[pidx].append('行動不能 反動')
                    self.pokemon[pidx].no_act()
                    continue

                # ねむり判定
                if self.pokemon[pidx].ailment == 'SLP':
                    delta = -2 if self.pokemon[pidx].ability == 'はやおき' else -1
                    self.pokemon[pidx].sleep_turn = max(0, self.pokemon[pidx].sleep_turn + delta)
                    self.log[pidx].append(f'ねむり 残り{self.pokemon[pidx].sleep_turn}ターン')
                    if self.pokemon[pidx].sleep_turn == 0:
                        # ねむり解除
                        self.set_ailment(pidx)
                    elif move.name not in PokeDB.move_category['sleep']:
                        # 行動不能
                        self.pokemon[pidx].no_act()
                        continue

                # こおり判定
                elif self.pokemon[pidx].ailment == 'FLZ':
                    if move.name in PokeDB.move_category['unfreeze'] or self._random.random() < 0.2:
                        # こおり解除
                        self.set_ailment(pidx)
                    else:
                        self.pokemon[pidx].no_act()
                        self.log[pidx].append('行動不能 こおり')
                        continue

                # なまけ判定
                if self.pokemon[pidx].ability == 'なまけ':
                    self.pokemon[pidx].ability.count += 1
                    if self.pokemon[pidx].ability.count % 2 == 0:
                        self.pokemon[pidx].no_act()
                        self.log[pidx].append('行動不能 なまけ')
                        continue

                # ひるみ判定
                if self._flinch:
                    self.pokemon[pidx].no_act()
                    self.log[pidx].append('行動不能 ひるみ')
                    if self.pokemon[pidx].ability == 'ふくつのこころ':
                        self.activate_ability(pidx)
                    continue

                # 挑発などにより、本来選択できない技が選ばれていれば中断する
                if self.pokemon[pidx].unresponsive_turn == 0:
                    is_choosable, reason = self.can_choose_move(pidx, move)
                    if not is_choosable:
                        self.pokemon[pidx].no_act()
                        self.log[pidx].append(f'{move} 不発 ({reason})')
                        continue

                # こんらん判定
                if self.pokemon[pidx].condition['confusion']:
                    self.pokemon[pidx].condition['confusion'] -= 1
                    self.log[pidx].append(f"こんらん 残り{self.pokemon[pidx].condition['confusion']}ターン")

                    # 自傷判定
                    if self._random.random() < 0.25:
                        mv = Move('わるあがき')
                        oneshot_damages = self.oneshot_damages(pidx, mv, self_harm=True)
                        self.add_hp(pidx, -self._random.choice(oneshot_damages), move=mv)
                        self.pokemon[pidx].no_act()
                        self.log[pidx].insert(-1, 'こんらん自傷')
                        continue

                # しびれ判定
                if self.pokemon[pidx].ailment == 'PAR' and self._random.random() < 0.25:
                    self.pokemon[pidx].no_act()
                    self.log[pidx].append('行動不能 しびれ')
                    continue

                # メロメロ判定
                if self.pokemon[pidx].condition['meromero'] and self._random.random() < 0.5:
                    self.pokemon[pidx].no_act()
                    self.log[pidx].append('行動不能 メロメロ')
                    continue

                # --- ここで行動できることが確定 ---

                # PP消費
                if move != 'わるあがき':
                    # PPを消費する技の確定
                    self.pokemon[pidx].expended_moves.append(move)

                    # 命令できる状態ならPPを消費する
                    if self.pokemon[pidx].unresponsive_turn == 0:
                        move.add_pp(-2 if self.pokemon[not pidx].ability == 'プレッシャー' else -1)
                        move.observed = True  # 観測
                        self.log[pidx].append(f'{move} PP {move.pp}')

                # ねごとによる技の変更
                if move == 'ねごと':
                    if self.can_execute_move(pidx, move):
                        move = self._random.choice(self.pokemon[pidx].negoto_moves())
                        move_class = self.pokemon[pidx].eff_move_class(move)
                        move.observed = True  # 観測
                        self.log[pidx].append(f'ねごと -> {move}')
                    else:
                        self.move_succeeded[pidx] = False

                # まもる技の連発と、場に出たターンしか使えない技の失敗
                for category in ['protect', 'first_turn']:
                    if not self.can_execute_move(pidx, move, category=category):
                        self.move_succeeded[pidx] = False

                # 発動する技の確定
                self.pokemon[pidx].executed_move = move if self.move_succeeded[pidx] else None

                # こだわり固定
                if (self.pokemon[pidx].item.name[:4] == 'こだわり' or self.pokemon[pidx].ability == 'ごりむちゅう'):
                    self.pokemon[pidx].choice_locked = True

                # 技の発動失敗
                # 本来、じばく技の判定はリベロ判定の後だが、実装の簡略化のためにまとめて行う
                self.move_succeeded[pidx] &= self.can_execute_move(pidx, move)

                # リベロ判定
                if self.pokemon[pidx].ability.name in ['へんげんじざい', 'リベロ'] and self.move_succeeded[pidx]:
                    self.activate_ability(pidx)

                # 溜め技
                if move.name in PokeDB.move_category['charge'] + PokeDB.move_category['hide']:
                    # 溜め判定
                    self.pokemon[pidx].unresponsive_turn = int(self.pokemon[pidx].unresponsive_turn == 0)

                    # 溜めの処理
                    if self.pokemon[pidx].unresponsive_turn and not self.charge_move(pidx, move):
                        continue  # 行動不能

                # 隠れ状態の解除
                self.pokemon[pidx].hidden = False

                # HPコストを払う技
                if move.name in PokeDB.move_value['cost'] and self.move_succeeded[pidx] and \
                        self.activate_move_effect(pidx, move, category='cost'):
                    # 勝敗判定
                    if self.get_winner() is not None:
                        return

                # 技が無効なら中断
                if not self.move_succeeded[pidx]:
                    self.log[pidx].append(f'{move} 失敗')
                    continue

                # 相手のまもる技により攻撃を防がれたら中断
                if self.did_protect_succeed(self, pidx, move):
                    continue

                # 技の発動回数の確定
                self.n_strikes = self.num_strikes(pidx, move)
                if self.n_strikes > 1:
                    self.log[pidx].append(f'{self.n_strikes}発')

                # 命中判定
                is_hit = self._random.random() < self.get_hit_probability(pidx, move)

                for i in range(self.n_strikes):
                    # 一部の連続技の命中判定
                    if i > 0 and PokeDB.move_combo[move.name][1] in [3, 10]:
                        is_hit = self._random.random() < self.get_hit_probability(pidx, move)

                    # 技を外したら中断
                    if not is_hit:
                        if i == 0:
                            # 1発目の外し
                            self.on_miss(pidx, move)
                        else:
                            # 連続技の中断
                            self.log[pidx].append(f'{i}ヒット')
                        break

                    if move.cls in ['phy', 'spe']:
                        # 攻撃技の処理
                        self.process_attack_moves(pidx, move, combo_count=i)
                    else:
                        # 変化技の処理
                        self.process_status_moves(pidx, move)

                    # 無効化特性の処理
                    self.process_negating_abilities(pidx)

                    # 即時アイテムの判定 (攻撃中)
                    for i in [pidx, not pidx]:
                        if self.pokemon[i].item.immediate and self.pokemon[i].hp:
                            self.activate_item(i)

                    # どちらか一方が瀕死なら攻撃を中断
                    if self.pokemon[pidx].hp * self.pokemon[not pidx].hp == 0:
                        break

                # 技の発動後の処理
                self.pokemon[pidx].active_turn += 1
                self.log[pidx].append(f"{move} {'成功' if self.move_succeeded[pidx] else '失敗'}")

                # ステラ強化タイプの消費
                self.consume_stellar(pidx, move)

                # 反動で動けない技の反動を設定
                if self.move_succeeded[pidx]:
                    self.activate_move_effect(pidx, move, category='immovable')

                if self.damage_dealt[pidx]:
                    # 攻撃側の特性発動
                    if self.pokemon[pidx].ability.name in [
                            'じしんかじょう', 'しろのいななき', 'じんばいったい', 'くろのいななき', 'マジシャン']:
                        self.activate_ability(pidx)

                    # 防御側の特性発動
                    if self.pokemon[not pidx].ability.name in ['へんしょく', 'ぎゃくじょう', 'いかりのこうら']:
                        self.activate_ability(not pidx, move)

                    self.pokemon[not pidx].berserk_triggered = False

                    # 被弾時のアイテム発動
                    if self.pokemon[not pidx].hp and \
                            self.pokemon[not pidx].item.name in ['レッドカード', 'アッキのみ', 'タラプのみ']:
                        self.activate_item(not pidx, move=move)

                    # 攻撃後のアイテム発動
                    if self.pokemon[pidx].item.name in ['いのちのたま', 'かいがらのすず']:
                        self.activate_item(pidx)

                # TODO ききかいひ・にげごし判定
                # TODO わるいてぐせ判定

                # だっしゅつボタン判定
                if self.pokemon[not pidx].item == 'だっしゅつボタン' and self.activate_item(not pidx):
                    self.breakpoint[not pidx] = 'ejectbutton'

            # だっしゅつボタンによる交代
            ejectbutton_triggered = False
            if self.breakpoint[not pidx] == 'ejectbutton':
                self.switch_pokemon(not pidx, command=switch_commands[not pidx])
                switch_commands[not pidx] = None  # コマンド破棄
                ejectbutton_triggered = True

            if not any(self.breakpoint):
                # 技の追加処理
                if move.name in ['アイアンローラー', 'アイススピナー', 'でんこうそうげき', 'もえつきる']:
                    self.activate_move_effect(pidx, move)

                # 交代技の処理
                if move.name in PokeDB.move_category['U-turn']:
                    if move.name in ['クイックターン', 'とんぼがえり', 'ボルトチェンジ'] and ejectbutton_triggered:
                        self.log[pidx].append(f'交代失敗')
                    elif self.move_succeeded[pidx]:
                        i = not pidx if move == 'すてゼリフ' and move_class[-4] == '1' and \
                            self.get_defender_ability(not pidx, move) == 'マジックミラー' else pidx
                        if self.switchable_indexes(i):
                            self.breakpoint[i] = f'Uturn_{pidx}'

            # 技による交代
            Uturned = False

            if (s := f'Uturn_{pidx}') in self.breakpoint:
                idx = self.breakpoint.index(s)
                baton = {}

                match move.name:
                    case 'しっぽきり':
                        baton['sub_hp'] = int(self.pokemon[idx].stats[0]/4)
                    case 'バトンタッチ':
                        if any(self.pokemon[idx].rank):
                            baton['rank'] = self.pokemon[idx].rank.copy()
                        if self.pokemon[idx].sub_hp:
                            baton['sub_hp'] = self.pokemon[idx].sub_hp
                        for s in list(self.pokemon[idx].condition.keys())[:8]:
                            if self.pokemon[idx].condition[s]:
                                baton[s] = self.pokemon[idx].condition[s]

                self.switch_pokemon(idx, command=switch_commands[idx], baton=baton)
                switch_commands[idx] = None  # コマンド破棄
                Uturned = True

            if not any(self.breakpoint):
                if not ejectbutton_triggered and not Uturned:
                    # だっしゅつパック判定 (わざ発動後)
                    if (pidxs := [i for i in self.speed_order if self.is_ejectpack_triggered(i)]):
                        self.breakpoint[pidxs[0]] = f'ejectpack_move_{pidx}'
                        self.pokemon[pidxs[0]].item.consume()
                        for i in pidxs:
                            self.pokemon[i].rank_dropped = False

            # だっしゅつパックによる交代
            if (s := f'ejectpack_move_{pidx}') in self.breakpoint:
                idx = self.breakpoint.index(s)
                self.switch_pokemon(idx, command=switch_commands[idx])
                switch_commands[idx] = None  # コマンド破棄

            if not any(self.breakpoint):
                # あばれる状態の判定
                self.activate_move_effect(pidx, move, category='rage')

                # のどスプレー判定
                if self.pokemon[pidx].hp and self.pokemon[pidx].item == 'のどスプレー':
                    self.activate_item(pidx, move=move)

                # 即時アイテムの判定 (手番が移る直前)
                if self.pokemon[pidx].item.immediate and self.pokemon[pidx].hp:
                    self.activate_item(pidx)

                # 後手が瀕死なら中断
                if self.pokemon[not pidx].hp == 0:
                    break

        if not any(self.breakpoint):
            # ターン終了時の処理
            self.process_turn_end()

            # 勝敗判定
            if self.get_winner() is not None:
                return

            # だっしゅつパック判定 (ターン終了時)
            if (pidxs := [i for i in self.speed_order if self.is_ejectpack_triggered(i)]):
                self.breakpoint[pidxs[0]] = 'ejectpack_end'
                self.pokemon[pidxs[0]].item.consume()
                for i in pidxs:
                    self.pokemon[i].rank_dropped = False

        # だっしゅつパックによる交代
        if (s := 'ejectpack_end') in self.breakpoint:
            pidx = self.breakpoint.index(s)
            self.switch_pokemon(pidx, command=switch_commands[pidx])
            switch_commands[pidx] = None  # コマンド破棄

        # 場のポケモンが瀕死なら交代
        while self.get_winner() is None:
            pidxs = []

            # 交代するプレイヤーを決定
            if not any(self.breakpoint):
                pidxs = [pidx for pidx in range(2) if self.pokemon[pidx].hp == 0]
                for pidx in pidxs:
                    self.breakpoint[pidx] = 'fainting'
            else:
                pidxs = [pidx for pidx in range(2) if self.breakpoint[pidx] == 'fainting']

            if not pidxs:
                break

            # 交代
            for pidx in pidxs:
                self.switch_pokemon(pidx, command=switch_commands[pidx], landing=False)
                switch_commands[pidx] = None  # コマンド破棄

            # 両者が死に出しした場合は素早さ順に処理する
            if len(pidxs) > 1:
                pidxs = self.speed_order

            # 着地処理
            for pidx in pidxs:
                self.land(pidx)

        # このターンに入力されたコマンドを記録
        self.record_command()

    def write(self, filename: str):
        """試合のログを書き出す"""
        with open(filename, 'w', encoding='utf-8') as fout:
            fout.write(json.dumps(self.game_log, ensure_ascii=False))

    def replay(filename: str, mute: bool = False) -> Battle:
        """ログから試合を再現する"""
        with open(filename, encoding='utf-8') as fin:
            log = json.load(fin)
            mode = BattleMode(log['mode'])

            if mode != BattleMode.SIM:
                warnings.warn(f"BattleMode.SIMモードのみリプレイ可能")
                return

            if not mute:
                print(f"{'-'*50}\nリプレイ {filename}\n{'-'*50}")

            # Battleを生成
            battle = Battle(mode=mode, n_selection=log['n_selection'], seed=log['seed'])

            # ポケモンを再現
            for pidx in range(2):
                battle.selection_indexes[pidx] = log[f"selection_indexes_{pidx}"]
                for d in log[f"team_{pidx}"]:
                    p = Pokemon()
                    p.load(d)
                    battle.player[pidx].team.append(p)

                if not mute:
                    for p, i in enumerate(battle.player[pidx].team):
                        print(f"Player_{pidx} #{i} {p}\n")

            if not mute:
                print('-'*50)

            # 試合の再現
            while (key := f'Turn{battle.turn}') in log:
                # 交代を予約
                battle.reserved_switches = log[key]['switch_history']

                # コマンドにしたがってターンを進める
                battle.proceed_turn(commands=log[key]['command'])

                # 行動した順にログ表示
                if not mute:
                    print(f'ターン{battle.turn}')
                    for pidx in [battle.first_player_idx, not battle.first_player_idx]:
                        print(f'\tPlayer {int(pidx)}',
                              battle.log[pidx], battle.damage_log[pidx])

        return battle

    def get_winner(self, timeup: bool = False) -> int:
        """
        勝敗を判定する

        Parameters
        ----------
        timeup : bool, optional
            TrueならTOD判定を行う, by default False

        Returns
        -------
        bool
            勝者のプレイヤー番号
        """

        if self._winner is not None:
            return self._winner

        TOD_scores = [self.get_TOD_score(pidx) for pidx in range(2)]

        if 0 in TOD_scores or self.turn == self.max_turn or timeup:
            self._winner = TOD_scores.index(max(TOD_scores))
            self.log[self.winner].append('勝ち')
            self.log[not self.winner].append('負け')

            # このターンに入力されたコマンドを記録
            self.record_command()
            self.game_log['winner'] = self.winner

        return self._winner

    def get_TOD_score(self, player_idx: int, alpha: float = 1) -> float:
        """
        TODスコア = (残数) + alpha * (残りHP割合)
        """

        n_alive, full_hp, total_hp = 0, 0, 0

        for p in self.selected_pokemons(player_idx):
            full_hp += p.stats[0]
            total_hp += p.hp
            if p.hp:
                n_alive += 1

        return n_alive + alpha * total_hp / full_hp

    def available_commands(self, player_idx: int, phase: str = None) -> list[int | BattleMode]:
        """
        選択可能なコマンドのリストを返す

        Parameters
        ----------
        pidx : int
            プレイヤー番号
        phase : 'selection' or 'battle' or 'switch'
            Noneなら現在のphaseを参照する

        Returns
        ----------
        list[int | BattleMode]
            選択可能なコマンド

            選出フェーズ
                n                               : n番目のポケモンを選出

            対戦フェーズ
                CommandRange['move'][n]         : n番目の技を選択
                CommandRange['terastal'][n]     : テラスタルしてn番目の技を選択
                CommandRange['switch'][n]       : Player.teamのn番目のポケモンに交代
                Command.STRUGGLE                : わるあがき
                Command.IGNORE                  : 命令不可
        """

        p = self.pokemon[player_idx]
        commands = []

        match (phase := phase or self.phase):
            case 'selection':
                return list(range(len(self.player[player_idx].team)))

            case 'battle':
                if p.unresponsive_turn:
                    return [Command.IGNORE]

                # 技を選択
                for i, move in enumerate(p.moves):
                    if self.can_choose_move(player_idx, move)[0]:
                        commands.append(i)

                # テラスタルして技を選択
                if self.can_terastallize(player_idx):
                    commands += [cmd + 10 for cmd in commands]

                # 交代
                if not self.is_caught(player_idx):
                    commands += [i + CommandRange['switch'][0]
                                 for i in self.switchable_indexes(player_idx)]

                # わるあがき
                if not commands:
                    commands = [Command.STRUGGLE]

            case 'switch':
                commands += [i + CommandRange['switch'][0] for i in self.switchable_indexes(player_idx)]

        if not commands:
            # 選択できるコマンドがなければエラー
            print(f"{'-'*50}\n{phase=}")
            for player_idx in self.action_order:
                print(f'\tPlayer_{int(player_idx)}', self.log[player_idx], self.damage_log[player_idx])
            print(f"{self.pokemon[player_idx]}")
            raise Exception(f"No available command for Player_{int(player_idx)}")

        return commands

    def record_command(self):
        """このターンに入力されたコマンドを記録"""
        self.game_log[f'Turn{self.turn - 1}'] = {
            'command': self.command,
            'switch_history': self.switch_history
        }

    def cmd2str(self, player_idx: int, command) -> str:
        """コマンドを文字列に変換"""
        if command in CommandRange['move']:
            return self.pokemon[player_idx].moves[command].name

        elif command in CommandRange['terastal']:
            return f"T{self.pokemon[player_idx].moves[command - CommandRange['terastal'][0]].name}"

        elif command in CommandRange['switch']:
            return f"{self.player[player_idx].team[command - CommandRange['switch'][0]].display_name}交代"

        elif command == Command.STRUGGLE:
            return "わるあがき"

        elif command == Command.IGNORE:
            return "命令不可"

        elif command == Command.SKIP:
            return "行動スキップ"

        else:
            warnings.warn(f"Invalid command {command}")
            return

    def get_command(self, player_idx: int = None, p: Pokemon = None,
                    move: Move = None, switch: Pokemon = None) -> int:
        """技や交代先のポケモンをコマンドに変換"""
        if player_idx is not None:
            p = self.pokemon[player_idx]

        if move and (mv := p.find_move(move)):
            return p.moves.index(mv) + 10*p.terastal

        if switch in self.player[player_idx].team:
            return 100 + self.player[player_idx].team.index(switch)

    def switchable_indexes(self, player_idx: int) -> list[int]:
        """交代可能なポケモンのインデックスのリストを返す"""
        indexes = []
        for i in self.selection_indexes[player_idx]:
            p = self.player[player_idx].team[i]
            if p.hp and p != self.pokemon[player_idx]:
                indexes.append(i)
        return indexes

    def update_action_order(self):
        """行動順を更新する"""
        action_speed = [0] * 2

        for pidx, p in enumerate(self.pokemon):
            # 素早さ順 (1e-2)
            action_speed[pidx] -= self.speed_order.index(pidx) * 1e-2

            # 行動スキップ (1e+3)
            if self.command[pidx] == Command.SKIP:
                action_speed[pidx] += 1e3
                continue

            # 交代 (1e+1)
            if self.command[pidx] in CommandRange['switch']:
                action_speed[pidx] += 1e1
                continue

            if self.command[pidx] in CommandRange['battle']:
                # コマンドで指定された技
                self.move[pidx] = p.moves[self.command[pidx] % 10]
            elif self.command[pidx] == Command.STRUGGLE:
                # わるあがき
                self.move[pidx] = Move('わるあがき')
            elif self.command[pidx] == Command.IGNORE:
                if (mv := p.executed_move) and mv.name in PokeDB.move_category['immovable']:
                    # 反動で動けない
                    self.move[pidx] = None
                    self.pokemon[pidx].unresponsive_turn = 0
                else:
                    # 前ターンと同じ技
                    self.move[pidx] = mv

            if not self.move[pidx]:
                continue

            # 技の優先度 (1e-1~1e0)
            self._move_speed[pidx] = self.get_move_speed(pidx, self.move[pidx])
            action_speed[pidx] += self._move_speed[pidx]

        self.first_player_idx = int(action_speed[0] < action_speed[1])
        self.action_order = [self.first_player_idx, not self.first_player_idx]

    def update_speed_order(self):
        """素早さ順を更新する"""
        # 素早さを取得
        speeds = []
        for pidx in range(2):
            speeds.append(self.get_speed(pidx))
            if self.condition['trickroom']:
                speeds[pidx] = 1/speeds[pidx]

        # 同速判定
        if speeds[0] == speeds[1]:
            pidx = self._random.randint(0, 1)
            speeds[pidx] += 1
            self.log[pidx].append('同速+1')

        # 素早さ順
        self.speed_order = [speeds.index(max(speeds)), speeds.index(min(speeds))]

    def estimate_opponent_speed(self, player_idx):
        """行動順から相手のポケモンの素早さを推定する"""
        opp = self.pokemon[not player_idx]
        masked = opp if self.open_sheet else opp.masked()

        # 観測可能な相手のS補正値
        r_speed = self.get_speed(player_idx, p=masked) / masked.stats[5]

        # 相手のS = 自分のS / 相手のS補正値
        speed = self.get_speed(player_idx) / r_speed

        # S推定値を更新
        opp.set_speed_limit(speed, first_act=(player_idx != self.first_player_idx))

        self.log[player_idx].append('先手' if player_idx == self.first_player_idx else '後手')

    def get_hit_probability(self, atk_idx: int, move: Move) -> int:
        """命中率"""
        def_idx = not atk_idx
        attacker, defender = self.pokemon[atk_idx], self.pokemon[def_idx]
        def_ability = self.get_defender_ability(def_idx, move)

        # 必中
        if attacker.lockon or 'ノーガード' in attacker.ability.name + def_ability.name or \
            (self.get_weather(def_idx) == 'rainy' and move.name in PokeDB.move_category['rainy_hit']) or \
                (self.get_weather() == 'snow' and move == 'ふぶき') or \
                (move == 'どくどく' and 'どく' in attacker.types):
            return 1

        # 隠れる技
        if defender.hidden and defender.executed_move:
            match defender.executed_move.name:
                case 'あなをほる':
                    if move.name not in ['じしん', 'マグニチュード']:
                        return 0
                case 'そらをとぶ' | 'とびはねる':
                    if move.name not in ['かぜおこし', 'かみなり', 'たつまき', 'スカイアッパー', 'うちおとす', 'ぼうふう', 'サウザンアロー']:
                        return 0
                case 'ダイビング':
                    if move.name not in ['なみのり', 'うずしお']:
                        return 0

        # ぜったいれいど
        if move.name in PokeDB.move_category['one_ko']:
            return 0.2 if move == 'ぜったいれいど' and 'こおり' not in attacker.types else 0.3

        # 技の命中率
        prob = move.hit

        if self.get_weather(atk_idx) == 'sunny' and move.name in ['かみなり', 'ぼうふう']:
            prob *= 0.5
        if def_ability == 'ミラクルスキン' and 'sta' in move.cls and move.hit <= 100:
            prob = min(prob, 50)

        # 命中補正
        m = 4096

        if self.condition['gravity']:
            m = ut.round_half_up(m*6840/4096)

        match attacker.ability.name:
            case 'はりきり':
                if move.cls == 'phy':
                    m = ut.round_half_up(m*3277/4096)
            case 'ふくがん':
                m = ut.round_half_up(m*5325/4096)
            case 'しょうりのほし':
                m = ut.round_half_up(m*4506/4096)

        match def_ability.name:
            case 'ちどりあし':
                if defender.condition['confusion']:
                    m = ut.round_half_up(m*0.5)
            case 'すながくれ':
                if self.get_weather() == 'sandstorm':
                    m = ut.round_half_up(m*3277/4096)
            case 'ゆきがくれ':
                if self.get_weather() == 'snow':
                    m = ut.round_half_up(m*3277/4096)

        match attacker.item.name:
            case 'こうかくレンズ':
                m = ut.round_half_up(m*4505/4096)
            case 'フォーカスレンズ':
                if atk_idx != self.first_player_idx:
                    m = ut.round_half_up(m*4915/4096)

        if defender.item.name in ['のんきのおこう', 'ひかりのこな']:
            m = ut.round_half_up(m*3686/4096)

        # ランク補正
        delta = attacker.rank[6]*(def_ability != 'てんねん')
        if attacker.ability.name not in ['しんがん', 'てんねん', 'するどいめ', 'はっこう'] and \
                move.name not in PokeDB.move_category['ignore_rank']:
            delta -= defender.rank[7]
        delta = max(-6, min(6, delta))
        r = (3+delta)/3 if delta >= 0 else 3/(3-delta)

        return int(ut.round_half_down(prob*m/4096)*r)/100

    def get_critical_probability(self, atk_idx: int, move: Move) -> float:
        """急所確率"""
        def_idx = not atk_idx
        attacker, defender = self.pokemon[atk_idx], self.pokemon[def_idx]

        # 急所無効
        if self.get_defender_ability(not atk_idx, move) in ['シェルアーマー', 'カブトアーマー'] or \
                move.name in PokeDB.move_category['one_ko']:
            return 0

        m = attacker.condition['critical']

        match attacker.ability.name:
            case 'きょううん':
                m += 1
            case 'ひとでなし':
                if defender.ailment == 'PSN':
                    m += 3

        if attacker.item.name in ['するどいツメ', 'ピントレンズ']:
            m += 1

        if move.name in PokeDB.move_category['critical']:
            m += 3
        elif move.name in PokeDB.move_category['high_critical']:
            m += 1

        return 1/24*(m == 0) + 0.125*(m == 1) + 0.5*(m == 2) + 1*(m >= 3)

    def get_defender_ability(self, def_idx: int, move: Move = None) -> Ability:
        """防御側のポケモンの実効的な特性を返す"""
        attacker, defender = self.pokemon[not def_idx], self.pokemon[def_idx]

        if not move or defender.item == 'とくせいガード' or defender.ability.undeniable:
            return defender.ability

        if move.name in ['シャドーレイ', 'フォトンゲイザー', 'メテオドライブ'] or \
            attacker.ability.name in ['かたやぶり', 'ターボブレイズ', 'テラボルテージ'] or \
                (attacker.ability == 'きんしのちから' and 'sta' in move.cls):
            return Ability()

        return defender.ability

    def get_move_type(self, atk_idx: int, move: Move) -> str:
        """技発動時の実効的なタイプ"""
        attacker = self.pokemon[atk_idx]

        if move.name in ['テラバースト', 'テラクラスター'] and attacker.terastal:
            return attacker.terastal

        match attacker.ability.name:
            case 'うるおいボイス':
                if move.name in PokeDB.move_category['sound']:
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
                t = {'sunny': 'ほのお', 'rainy': 'みず',
                     'snow': 'こおり', 'sandstorm': 'いわ'}
                if (weather := self.get_weather(atk_idx)):
                    return t[weather]
            case 'さばきのつぶて' | 'めざめるダンス':
                return attacker.types[0]
            case 'ツタこんぼう':
                if 'オーガポン(' in attacker.name:
                    return attacker.org_types[-1]
            case 'レイジングブル':
                return attacker.types[-1]

        return move.type

    def get_move_speed(self, atk_idx: int, move: Move) -> int:
        """技による行動速度. 上位優先度(1e0)+下位優先度(1e-1)"""
        speed = move.priority

        attacker = self.pokemon[atk_idx]

        # 上位優先度 (1e0)
        match attacker.ability.name:
            case 'いたずらごころ':
                if 'sta' in move.cls:
                    speed += 1
                    self.log[atk_idx].append(attacker.ability.name)
            case 'はやてのつばさ':
                if attacker.hp_ratio == 1 and move.type == 'ひこう':
                    speed += 1
                    self.log[atk_idx].append(attacker.ability.name)
            case 'ヒーリングシフト':
                if move.name in PokeDB.move_category['heal'] or move.name in PokeDB.move_value['drain']:
                    speed += 3
                    self.log[atk_idx].append(attacker.ability.name)

        if move == 'グラススライダー' and self.condition['glassfield']:
            speed += 1

        # 下位優先度 (1e-1)
        if attacker.ability == 'きんしのちから' and 'sta' in move.cls:
            speed -= 1e-1
            self.log[atk_idx].append(attacker.ability.name)
        elif attacker.ability == 'クイックドロウ' and self._random.random() < 0.3:
            speed += 1e-1
            self.log[atk_idx].append(attacker.ability.name)
        elif attacker.item == 'せんせいのツメ' and self.activate_item(atk_idx):
            speed += 1e-1
        elif attacker.item == 'イバンのみ' and self.activate_item(atk_idx):
            speed += 1e-1
        else:
            if attacker.ability == 'あとだし':
                speed -= 1e-1
                self.log[atk_idx].append(attacker.ability.name)
            if attacker.item.name in ['こうこうのしっぽ', 'まんぷくおこう']:
                speed -= 1e-1

        return speed

    def get_speed(self, player_idx: int, p: Pokemon = None) -> int:
        """場のポケモンまたは{p}の素早さ実効値を返す"""
        if p is None:
            p = self.pokemon[player_idx]

        speed = int(p.stats[5]*p.rank_correction(5))

        if p.boosted_idx == 5:
            speed = int(speed*1.5)

        r = 4096

        match p.ability.name:
            case 'かるわざ':
                if p.ability.count:
                    r = ut.round_half_up(r*2)
            case 'サーフテール':
                if self.condition['elecfield']:
                    r = ut.round_half_up(r*2)
            case 'すいすい':
                if self.get_weather(player_idx) == 'rainy':
                    r = ut.round_half_up(r*2)
            case 'すなかき':
                if self.get_weather() == 'sandstorm':
                    r = ut.round_half_up(r*2)
            case 'スロースタート':
                r = ut.round_half_up(r*0.5)
            case 'はやあし':
                if p.ailment:
                    r = ut.round_half_up(r*1.5)
            case 'ゆきかき':
                if self.get_weather() == 'snow':
                    r = ut.round_half_up(r*2)
            case 'ようりょくそ':
                if self.get_weather(player_idx) == 'sunny':
                    r = ut.round_half_up(r*2)

        match p.item.name:
            case 'くろいてっきゅう':
                r = ut.round_half_up(r*0.5)
            case 'こだわりスカーフ':
                r = ut.round_half_up(r*1.5)

        if self.condition['oikaze'][player_idx]:
            r = ut.round_half_up(r*2)

        speed = ut.round_half_down(speed*r/4096)

        if p.ailment == 'PAR' and p.ability != 'はやあし':
            speed = int(speed*0.5)

        return speed

    def get_weather(self, player_idx: int = None) -> str:
        """現在の天候。{player_idx}を指定すると、ばんのうがさを考慮する"""
        if any(s in [p.ability.name for p in self.pokemon] for s in ['エアロック', 'ノーてんき']):
            return
        for s in PokeDB.weathers:
            if self.condition[s]:
                if player_idx and self.pokemon[player_idx].item == 'ばんのうがさ' and s in ['sunny', 'rainy']:
                    return
                return s

    def get_field(self) -> str:
        """現在のフィールド"""
        for s in PokeDB.fields:
            if self.condition[s]:
                return s

    def get_hp_drain(self, player_idx: int, raw_amount: int, from_opponent: bool = True):
        """HP吸収量を補正する。{from_opponent}=Trueなら相手からHPを吸収したとみなす"""
        r = 5324/4096 if self.pokemon[player_idx].item == 'おおきなねっこ' else 1
        if from_opponent and self.pokemon[not player_idx].ability == 'ヘドロえき':
            r = -r
        return ut.round_half_up(raw_amount*r)

    def set_ailment(self, player_idx: int, ailment: str = None, move: Move = None,
                    badpoison: bool = False, safeguard: bool = True) -> bool:
        """場のポケモンを状態異常にする

        Parameters
        ----------
        player_idx: int

        ailment:  str
            状態異常。{ailment}=''なら状態異常を解除

        move: Move
            Noneでなければmoveによる変更とみなす

        badpoison: bool
            Trueならもうどく

        safeguard: bool
            Trueならしんぴのまもりを考慮

        Returns
        ----------
        bool
            状態異常が変更されたらTrue
        """
        opp_idx = not player_idx
        target, opp = self.pokemon[player_idx], self.pokemon[opp_idx]
        target_ability = self.get_defender_ability(player_idx, move)

        # 状態異常の解除
        if not ailment:
            if target.ailment:
                self.log[player_idx].append(f'{PokeDB.JPN[target.ailment]}解除')
                target.ailment = ''
                target.sleep_turn = 0
                return True
            else:
                return False

        # すべての状態異常を無効にする条件
        if target_ability in ['きよめのしお', 'ぜったいねむり'] or \
            (target_ability == 'リーフガード' and self.get_weather() == 'sunny') or \
                (target_ability == 'フラワーベール' and 'くさ' in target.types):
            self.log[player_idx].append(target_ability)
            return False

        if self.condition['mistfield'] and not self.is_float(player_idx):
            self.log[player_idx].append(PokeDB.JPN['mistfield'])
            return False

        if move == 'ねむる':
            if target.ailment == 'SLP':
                return False
        elif target .ailment or (safeguard and self.condition['safeguard'][player_idx]):
            return False

        # 特定の状態異常を無効にする条件
        match ailment:
            case 'PSN':
                if target_ability in ['めんえき', 'パステルベール']:
                    self.log[player_idx].append(target_ability)
                    return False
                if any(t in target.types for t in ['どく', 'はがね']) and \
                        not (opp.ability == 'ふしょく' and move and 'sta' in move.cls):
                    return False
            case 'PAR':
                if 'でんき' in target.types:
                    return False
                if target_ability == 'じゅうなん':
                    self.log[player_idx].append(target_ability)
                    return False
                if move == 'でんじは' and 'じめん' in target.types:
                    return False
            case 'BRN':
                if 'ほのお' in target.types:
                    return False
                if target_ability in ['すいほう', 'ねつこうかん', 'みずのベール']:
                    self.log[player_idx].append(target_ability)
                    return False
            case 'SLP':
                if target_ability in ['スイートベール', 'やるき', 'ふみん']:
                    self.log[player_idx].append(target_ability)
                    return False
                if self.condition['elecfield'] and not self.is_float(player_idx):
                    return False
            case 'FLZ':
                if 'こおり' in target.types:
                    return False
                if target_ability == 'マグマのよろい':
                    self.log[player_idx].append(target_ability)
                    return False
                if self.get_weather() == 'sunny':
                    return False

        target.ailment = ailment
        self.log[player_idx].append(PokeDB.JPN[target.ailment])

        match target.ailment:
            case 'PSN':
                target.condition['badpoison'] = int(badpoison)
                if opp.ability == 'どくくぐつ' and move and self.set_condition(player_idx, 'confusion'):
                    self.log[player_idx].insert(-1, opp.ability.name)
            case 'SLP':
                target.sleep_turn = 3 if move == 'ねむる' else self._random.randint(
                    2, 4)
                target.condition['nemuke'] = 0
                target.unresponsive_turn = 0

        if target.ability == 'シンクロ' and move and move != 'ねむる' and self.set_ailment(opp_idx, ailment):
            self.log[player_idx].insert(-1, target.ability.name)

        return True

    def set_weather(self, player_idx: int, weather: str = None) -> bool:
        """天候を変える"""
        current_weather = [s for s in PokeDB.weathers if self.condition[s]] or ['']
        current_weather = current_weather[0]

        if weather == current_weather:
            return False

        # ターン延長アイテムの判定
        turn = 8 if weather and self.pokemon[player_idx].item == PokeDB.weather2stone[weather] else 5

        # 変更
        for s in PokeDB.weathers:
            self.condition[s] = turn if s == weather else 0

        if weather:
            self.log[player_idx].append(f'{PokeDB.JPN[weather]} {self.condition[weather]}ターン')
        else:
            self.log[player_idx].append(f'{PokeDB.JPN[current_weather]}解除')

        for idx, p in enumerate(self.pokemon):
            if p.ability == 'こだいかっせい':
                self.activate_ability(idx)

        return True

    def set_field(self, player_idx: int, field: str = None) -> bool:
        """フィールドを変更する"""
        current_field = [s for s in PokeDB.fields if self.condition[s]] or ['']
        current_field = current_field[0]

        if field == current_field:
            return False

        # ターン延長アイテムの判定
        turn = 8 if field and self.pokemon[player_idx].item == 'グランドコート' else 5

        # 変更
        for s in PokeDB.fields:
            self.condition[s] = turn if s == field else 0

        if field:
            self.log[player_idx].append(f'{PokeDB.JPN[field]} {self.condition[field]}ターン')
        else:
            self.log[player_idx].append(f'{PokeDB.JPN[current_field]}解除')

        for idx, p in enumerate(self.pokemon):
            if p.ability == 'クォークチャージ':
                self.activate_ability(idx)

        return True

    def set_condition(self, player_idx: int, condition: str, move: Move = None) -> bool:
        """場のポケモンの状態を変更

        Parameters
        ----------
        player_idx: int

        condition: str
            変更する状態

        move: Move
            Noneでなければ技による変化とみなす

        Returns
        ----------
        : bool
            変更できたらTrue
        """

        opp_idx = not player_idx
        target, opp = self.pokemon[player_idx], self.pokemon[opp_idx]

        if target.condition[condition]:
            return False

        match condition:
            case 'confusion':
                if target.ability != 'マイペース':
                    target.condition['confusion'] = self._random.randint(2, 5)
                    self.log[player_idx].append('こんらん')
                    return True

            case 'nemuke':
                if target.ailment or self.condition['safeguard'][player_idx] or \
                    target.ability.name in ['ふみん', 'やるき', 'スイートベール', 'きよめのしお', 'ぜったいねむり', 'リミットシールド'] or \
                    (target.ability == 'リーフガード' and self.get_weather() == 'sunny') or \
                    (target.ability == 'フラワーベール' and 'くさ' in target.types) or \
                        (self.get_field() == 'elecfield' and not self.is_float(player_idx)):
                    return False
                else:
                    target.condition['nemuke'] = 2
                    return True

            case 'meromero':
                if target.gender.value * opp.gender.value == -1 and \
                        self.get_defender_ability(player_idx, move) not in ['アロマベール', 'どんかん']:
                    target.condition['meromero'] = 1
                    self.log[player_idx].append('メロメロ')
                    if target.item == 'あかいいと' and self.set_condition(opp_idx, 'meromero'):
                        self.log[player_idx].insert(-1, 'あかいいと発動')
                    return True

        return False

    def can_terastallize(self, player_idx: int) -> bool:
        """テラスタル可能ならTrue"""
        return not any(p.terastal for p in self.selected_pokemons(player_idx))

    def can_choose_move(self, player_idx: int, move: Move) -> list[bool, str]:
        """[技を選択できればTrue, 選択できない理由] を返す"""
        p = self.pokemon[player_idx]

        if move.pp == 0:
            return [False, 'PP切れ']
        if p.condition['encore'] and p.expended_moves and move != p.expended_moves[-1]:
            return [False, 'アンコール状態']
        if p.condition['healblock'] and (move.name in PokeDB.move_category['heal'] or move.name in PokeDB.move_value['drain']):
            return [False, 'かいふくふうじ状態']
        if p.condition['kanashibari'] and p.expended_moves and move == p.expended_moves[-1]:
            return [False, 'かなしばり状態']
        if p.condition['jigokuzuki'] and move.name in PokeDB.move_category['sound']:
            return [False, 'じごくづき状態']
        if p.condition['chohatsu'] and 'sta' in move.cls:
            return [False, 'ちょうはつ状態']
        if move.name in (PokeDB.move_category['unrepeatable'] + PokeDB.move_category['protect']) and \
                p.executed_move and move == p.executed_move:
            return [False, '連発不可']
        if p.choice_locked and p.expended_moves and move != p.expended_moves[-1]:
            return [False, 'こだわり状態']
        if p.item == 'とつげきチョッキ' and move.cls not in ['phy', 'spe']:
            return [False, 'とつげきチョッキ']

        return [True, '']

    def can_execute_move(self, atk_idx: int, move: Move, category: str = None) -> bool:
        def_idx = not atk_idx
        attacker, defender = self.pokemon[atk_idx], self.pokemon[def_idx]

        if category and move.name in PokeDB.move_category[category]:
            match category:
                case 'protect':
                    if attacker.executed_move and attacker.executed_move.name in PokeDB.move_category['protect']:
                        self.log[atk_idx].append('連続まもる')
                        return False
                case 'first_turn':
                    if attacker.active_turn:
                        return False

        match move.name:
            case 'ねごと':
                if attacker.ailment != 'SLP' or not attacker.negoto_moves():
                    return False
            case 'アイアンローラー':
                if not self.get_field():
                    return False
            case 'いびき':
                if attacker.ailment != 'SLP':
                    return False
            case 'じんらい' | 'ふいうち':
                if atk_idx != self.first_player_idx or not self.move[def_idx] or 'sta' in self.move[def_idx].cls:
                    return False
            case 'なげつける':
                if not attacker.item.active or not attacker.is_item_removable():
                    return False
            case 'はやてがえし':
                if atk_idx != self.first_player_idx or self._move_speed[def_idx] <= 0:
                    return False
            case 'ポルターガイスト':
                if not defender.item.active:
                    return False
                defender.item.observed = True  # 観測
            case 'じばく' | 'だいばくはつ' | 'ビックリヘッド' | 'ミストバースト':
                if 'しめりけ' in (abilities := [p.ability.name for p in self.pokemon]):
                    self.pokemon[abilities.index('しめりけ')].ability.observed = True  # 観測
                    return False

        # 特性による先制技無効
        if defender.ability.name in ['じょおうのいげん', 'テイルアーマー', 'ビビッドボディ'] and self._move_speed[atk_idx] > 0:
            defender.ability.observed = True  # 観測
            self.log[atk_idx].append(defender.ability.name)
            return False

        # サイコフィールドによる先制技無効
        if self.condition['psycofield'] and self._move_speed[atk_idx] > 0:
            self.log[atk_idx].append('行動不能 サイコフィールド')
            return False

        # あくタイプによるいたずらごころ無効
        if attacker.ability == 'いたずらごころ' and 'あく' in defender.types and \
            attacker.expended_moves and attacker.executed_move and \
                attacker.expended_moves[-1].cls[-3] == '1' or \
            ('sta' in attacker.expended_moves[-1].cls[-3] and attacker.expended_moves[-1].cls in ['phy', 'spe']):
            attacker.ability.observed = True  # 観測
            self.log[atk_idx].append('いたずらごころ無効')
            return False

        return True

    def can_inflict_move_effect(self, atk_idx: int, move: Move) -> bool:
        """相手に追加効果を与えることができる状態ならTrue"""
        def_idx = not atk_idx
        attacker, defender = self.pokemon[atk_idx], self.pokemon[def_idx]
        return attacker.ability != 'ちからずく' and defender.item != 'おんみつマント' and \
            self.get_defender_ability(def_idx, move) != 'りんぷん' and not self._substituted

    def can_be_flinched(self, player_idx):
        return player_idx != self.first_player_idx and self.pokemon[player_idx].ability != 'せいしんりょく'

    def is_float(self, player_idx: int) -> bool:
        """ふゆう状態ならTrue"""
        p = self.pokemon[player_idx]
        if p.item == 'くろいてっきゅう' or p.condition['anti_air'] or p.condition['neoharu'] or self.condition['gravity']:
            return False
        else:
            return 'ひこう' in p.types or p.ability == 'ふゆう' or p.item == 'ふうせん' or p.condition['magnetrise']

    def is_overcoat(self, player_idx: int, move: Move = None) -> bool:
        """ぼうじん状態ならTrue"""
        return self.pokemon[player_idx].item == 'ぼうじんゴーグル' or self.get_defender_ability(player_idx, move) == 'ぼうじん'

    def is_nervous(self, player_idx: int) -> bool:
        """きんちょうかん状態ならTrue"""
        return self.pokemon[not player_idx].ability.name in ['きんちょうかん', 'じんばいったい']

    def is_blowable(self, player_idx: int) -> bool:
        """強制交代可能ならTrue"""
        return self.switchable_indexes(player_idx) and \
            self.pokemon[player_idx].ability.name not in ['きゅうばん', 'ばんけん'] and \
            not self.pokemon[player_idx].condition['neoharu']

    def is_caught(self, player_idx: int) -> bool:
        """交代できない状態ならTrue"""
        target, opp = self.pokemon[player_idx], self.pokemon[not player_idx]

        if 'ゴースト' in target.types or target.ability == 'にげあし' or target.item == 'きれいなぬけがら':
            return False

        if target.condition['switchblock'] or target.condition['bind']:
            return True

        match opp.ability.name:
            case 'ありじごく':
                return not self.is_float(player_idx)
            case 'かげふみ':
                return target.ability != 'かげふみ'
            case 'じりょく':
                return 'はがね' in target.types

        return False

    def is_ejectpack_triggered(self, player_idx: int):
        return self.pokemon[player_idx].rank_dropped and self.switchable_indexes(player_idx)

    def switch_pokemon(self, player_idx: int, command: int = None, p: Pokemon = None, idx: int = None,
                       baton: dict = {}, landing=True):
        """場のポケモンを交代する
        """
        ability1 = ''

        # 控えに戻す
        if (p := self.pokemon[player_idx]):
            ability1 = p.ability
            p.bench_reset()

            # フォルムチェンジ
            if p.name == 'イルカマン(ナイーブ)':
                p.change_form('イルカマン(マイティ)')
                self.log[player_idx].append('-> マイティフォルム')

        # コマンドを取得
        if command:
            pass
        elif p in self.player[player_idx].team:
            command = self.player[player_idx].team.index(p) + 100
        elif idx is not None:
            command = idx + 100
        else:
            if self.reserved_switches[player_idx]:
                # 予約されているコマンドを使用
                command = self.reserved_switches[player_idx].pop(0)
            else:
                # 方策関数に従う
                self.phase = 'switch'
                command = self.player[player_idx].switch_command(
                    self.masked(player_idx, called=True))
                self.phase = None

            self.switch_history[player_idx].append(command)

        # 交代
        self.pokemon[player_idx] = self.player[player_idx].team[command-100]
        self.already_switched[player_idx] = True
        self.pokemon[player_idx].observed = True  # 観測
        self.log[player_idx].append(f'交代 -> {self.pokemon[player_idx].name}')
        self.breakpoint[player_idx] = None  # Breakpoint破棄

        # 相手の状態をリセット
        if (opp := self.pokemon[not player_idx]):
            if ability1 == 'かがくへんかガス':
                opp.ability.active = True
                if opp.ability.immediate:
                    self.activate_ability(not player_idx)
                self.log[not player_idx].append('かがくへんかガス解除')

            # バインド状態
            if opp.condition['bind']:
                opp.condition['bind'] = 0
                self.log[player_idx].append('バインド解除')

            # にげられない状態
            if opp.condition['switchblock']:
                opp.condition['switchblock'] = 0
                self.log[player_idx].append('にげられない解除')

        # バトン処理
        if baton:
            p = self.pokemon[player_idx]
            if 'sub_hp' in baton:
                p.sub_hp = baton['sub_hp']
                self.log[player_idx].append(f'継承 みがわり HP{baton["sub_hp"]}')
            if 'rank' in baton:
                p.rank = baton['rank']
                self.log[player_idx].append(f'継承 ランク {baton["rank"][1:]}')
            for s in list(p.condition.keys())[:8]:
                if s in baton:
                    p.condition[s] = baton[s]
                    self.log[player_idx].append(f'継承 {PokeDB.JPN[s]} {baton[s]}')

        # 行動順の更新
        self.update_speed_order()

        # 着地時の処理
        if landing:
            self.land(player_idx)

    def land(self, player_idx: int):
        """ポケモンが場に出たときの処理"""
        p = self.pokemon[player_idx]

        # 設置物の判定
        if p.item != 'あつぞこブーツ':
            if self.condition['stealthrock'][player_idx]:
                ratio = -int(self.defence_type_correction(not player_idx, 'ステルスロック') / 8)
                if self.add_hp(player_idx, ratio=ratio):
                    self.log[player_idx].insert(-1, 'ステルスロック')

            if not self.is_float(player_idx):
                if self.condition['makibishi'][player_idx]:
                    d = -int(p.stats[0] / (10-2*self.condition['makibishi'][player_idx]))
                    if self.add_hp(player_idx, d):
                        self.log[player_idx].insert(-1, 'まきびし')

                if self.condition['dokubishi'][player_idx]:
                    if 'どく' in p.types:
                        self.condition['dokubishi'][player_idx] = 0
                        self.log[player_idx].append('どくびし解除')
                    elif self.set_ailment(player_idx, 'PSN', badpoison=(self.condition['dokubishi'][player_idx] == 2)):
                        self.log[player_idx].append('どくびし接触')

                if self.condition['nebanet'][player_idx]:
                    if self.add_rank(player_idx, 5, -1, by_opponent=True):
                        self.log[player_idx].insert(-1, 'ねばねばネット')

        # 生死判定
        if p.hp == 0:
            return

        # 特性の発動
        for idx in [player_idx, not player_idx]:
            if not self.pokemon[idx].is_ability_protected():
                if self.pokemon[not idx].ability == 'かがくへんかガス' and self.pokemon[idx].item != 'とくせいガード':
                    # かがくへんかガス
                    self.pokemon[idx].ability.active = False
                    self.log[idx].append('かがくへんかガス 特性無効')
                    break

                elif self.pokemon[idx].ability == 'トレース' and self.pokemon[not idx].ability.unreproducible:
                    # トレース
                    self.pokemon[idx].ability.name = self.pokemon[not idx].ability.name
                    self.log[idx].append(f'トレース -> {self.pokemon[not idx].ability}')

            if self.pokemon[idx].ability.immediate:
                self.activate_ability(idx)

        # 即時アイテムの判定 (着地時)
        for idx in range(2):
            if self.pokemon[player_idx].item.immediate and self.pokemon[player_idx].hp:
                self.activate_item(player_idx)

    def add_hp(self, player_idx: int, value: int, ratio: float = None, move: Move = None) -> bool:
        """
        場のポケモンのHPを変更する

        Parameters
        ----------
        player_idx: int

        value: int
            HP変化量

        move: Move
            Noneでなければ技による変化とみなす

        Returns
        ----------
        : bool
            HPが変化したらTrue
        """
        p = self.pokemon[player_idx]

        if ratio is not None:
            value = int(p.stats[0] * ratio)

        if value == 0:
            return False

        # 回復
        elif value > 0:
            if p.hp_ratio == 1 or (p.condition['healblock'] and move and move != 'いたみわけ'):
                return False
            else:
                prev = p.hp
                p.hp = min(p.stats[0], p.hp + value)
                self.log[player_idx].append(f'HP +{p.hp - prev}')

        # ダメージ
        else:
            if p.hp == 0 or (not move and p.ability == 'マジックガード'):
                return False

            prev = p.hp
            p.hp = max(0, p.hp + value)
            self.log[player_idx].append(f'HP {p.hp - prev}')

            if move and move != 'わるあがき' and prev >= p.stats[0]/2 and p.hp_ratio <= 0.5:
                p.berserk_triggered = True

            # 回復実の判定
            if p.hp and p.item.name in PokeDB.recovery_fruits and \
                    move and move.name not in ['ついばむ', 'むしくい', 'やきつくす']:
                self.activate_item(player_idx)

        return True

    def add_rank(self, player_idx: int, stat_idx: int, value: int, rank_list: list[int] = [],
                 by_opponent: bool = False, can_chain: bool = False) -> list[int]:
        """
        場のポケモンの能力ランクを変動させる

        Parameters
        ----------
        player_idx: int

        stat_idx: int
            0,1,2,3,4,5,6,7
            H,A,B,C,D,S,命中,回避

        value: int
            変動量

        rank_list: [int]
            stat_idxまたはvalueが0なら、rank_listを参照して能力ランクを変動させる

        by_opponent: bool
            Trueなら相手による能力変化とみなす

        can_chain: bool
            Falseならミラーアーマーやものまねハーブが発動しない

        Returns
        ----------
        delta: [int]
            変動したランクのリスト
        """

        if (stat_idx == 0 or value == 0) and not any(rank_list):
            return []

        if not any(rank_list):
            rank_list = [0]*8
            rank_list[stat_idx] = value

        target = self.pokemon[player_idx]  # ランク変化する側
        p2 = self.pokemon[not player_idx]  # しかけた側
        delta = [0]*8
        reflection = [0]*8

        for i, v in enumerate(rank_list):
            if i == 0 or v == 0:
                continue

            if target.item == 'クリアチャーム' and v < 0 and by_opponent:
                if self.log[player_idx][-1] != target.item:
                    self.log[player_idx].append(target.item.name)
                continue

            if target.ability == 'あまのじゃく':
                v *= -1

            if target.rank[i]*v/abs(v) == 6:
                continue

            if v < 0 and by_opponent:
                if self.condition['whitemist'][player_idx]:
                    if self.log[player_idx][-1] != PokeDB.JPN['whitemist']:
                        self.log[player_idx].append(PokeDB.JPN['whitemist'])
                    continue

                match target.ability.name:
                    case 'クリアボディ' | 'しろいけむり' | 'メタルプロテクト':
                        if self.log[player_idx][-1] != target.ability.name:
                            self.log[player_idx].append(target.ability.name)
                        continue
                    case 'フラワーベール':
                        if self.condition['sunny']:
                            if self.log[player_idx][-1] != target.ability.name:
                                self.log[player_idx].append(target.ability.name)
                            continue
                    case 'かいりきバサミ':
                        if i == 1:
                            if self.log[player_idx][-1] != target.ability.name:
                                self.log[player_idx].append(target.ability.name)
                            continue
                    case 'はとむね':
                        if i == 2:
                            if self.log[player_idx][-1] != target.ability.name:
                                self.log[player_idx].append(target.ability.name)
                            continue
                    case 'しんがん' | 'するどいめ':
                        if i == 6:
                            if self.log[player_idx][-1] != target.ability.name:
                                self.log[player_idx].append(target.ability.name)
                            continue
                    case 'ミラーアーマー':
                        reflection[i] = v
                        continue

            prev = target.rank[i]
            target.rank[i] = max(-6, min(6, prev + v *
                                         (2 if target.ability == 'たんじゅん' else 1)))
            delta[i] = target.rank[i] - prev

        if any(reflection) and not can_chain and self.add_rank(not player_idx, 0, 0, rank_list=reflection, can_chain=True):
            self.log[player_idx].append(target.ability.name)

        if not any(delta):
            return []

        target.rank_dropped = any(v < 0 for v in delta)

        self.log[player_idx].append(Pokemon.rank2str(delta))

        if by_opponent and any([min(0, v) for v in delta]):
            match target.ability.name:
                case 'かちき':
                    if self.add_rank(player_idx, 3, +2):
                        self.log[player_idx].insert(-1, target.ability.name)
                case 'まけんき':
                    if self.add_rank(player_idx, 1, +2):
                        self.log[player_idx].insert(-1, target.ability.name)

        if any(pos_delta := [max(0, v) for v in delta]) and not can_chain:
            if p2.ability == 'びんじょう' and self.add_rank(not player_idx, 0, 0, rank_list=pos_delta, can_chain=True):
                self.log[not player_idx].insert(-1, p2.ability.name)
            if p2.item == 'ものまねハーブ' and self.add_rank(not player_idx, 0, 0, rank_list=pos_delta, can_chain=True):
                self.activate_item(not player_idx)

        return delta

    def charge_move(self, atk_idx: int, move: Move) -> bool:
        attacker = self.pokemon[atk_idx]

        if move.name in PokeDB.move_category['hide']:
            attacker.hidden = True
        elif move.name in ['メテオビーム', 'エレクトロビーム', 'ロケットずつき']:
            self.activate_move_effect(atk_idx, move)

        if (move.name in ['ソーラービーム', 'ソーラーブレード'] and self.get_weather(atk_idx) == 'sunny') or \
                (move == 'エレクトロビーム' and self.get_weather(atk_idx) == 'rainy'):
            # 溜め省略
            attacker.unresponsive_turn = 0
            self.log[atk_idx].append('溜め省略')
        elif attacker.item == 'パワフルハーブ' and self.activate_item(atk_idx):
            pass
        else:
            self.log[atk_idx].append('行動不能 溜め')
            return False

        return True

    def modify_damage(self, atk_idx: int):
        defender = self.pokemon[not atk_idx]

        # ダメージ上限 = 残りHP
        self.damage_dealt[atk_idx] = min(defender.hp, self.damage_dealt[atk_idx])

        # ダメージ修正
        if self._koraeru and self.damage_dealt[atk_idx] == defender.hp:
            # こらえる
            self.damage_dealt[atk_idx] -= 1
            self.move_succeeded[not atk_idx] = True
        elif defender.ability == 'がんじょう' and self.activate_ability(not atk_idx):
            pass
        elif defender.item in ['きあいのタスキ', 'きあいのハチマキ']:
            self.activate_item(not atk_idx)

    def process_attack_moves(self, atk_idx: int, move: Move, combo_count: int = None):
        def_idx = not atk_idx
        attacker, defender = self.pokemon[atk_idx], self.pokemon[def_idx]

        # 急所判定
        self._critical = self._random.random() < self._get_critical_probability(atk_idx, move)
        if self._critical:
            self.log[atk_idx].append('急所')

        if move.power > 0:
            # ダメージ計算
            r = 1
            if move == 'トリプルアクセル':
                r += combo_count

            oneshot_damages = self.oneshot_damages(atk_idx, move, critical=self._critical, power_scale=r)
            self.damage_dealt[atk_idx] = self._random.choice(oneshot_damages) if oneshot_damages else 0

            # ダメージが発生した状況を記録
            if self.damage_dealt[atk_idx] and not any(self.call_count):
                self.damage_logs.append(DamageLogger(self, atk_idx, move))

        else:
            # ダメージ計算が適用されない技の処理
            self.calculate_special_damage(atk_idx, move)

            # 勝敗判定 (いのちがけ処理)
            if self.get_winner() is not None:
                return

        # ダメージが0なら中断
        if not self.damage_dealt[atk_idx]:
            attacker.unresponsive_turn = 0
            self.move_succeeded[atk_idx] = False
            return

        # 壁破壊
        self.activate_move_effect(atk_idx, move, category='wall_break')

        # ダメージに関与したアイテムの消費
        for i, p in enumerate(self.pokemon):
            if p.item.name in self.damage_log[i]:
                self.damage_log[i].remove(f'{p.item}')
                p.item.consume()

        # みがわり判定
        self._substituted = defender.sub_hp and attacker.ability != 'すりぬけ' and \
            move.name not in PokeDB.move_category['sound']

        # ダメージ処理
        if self._substituted:
            # みがわり被弾
            self.damage_dealt[atk_idx] = min(defender.sub_hp, self.damage_dealt[atk_idx])
            defender.sub_hp -= self.damage_dealt[atk_idx]

            if defender.sub_hp:
                self.log[def_idx].append(f'みがわりHP {defender.sub_hp}')
            else:
                self.log[def_idx].append(f'みがわり消滅')

        elif self.get_defender_ability(def_idx, move) == 'ばけのかわ':
            # ばけのかわ被弾
            self.damage_dealt[atk_idx] = 0
            self.add_hp(def_idx, ratio=-0.125)
            self.log[def_idx].insert(-1, defender.ability.name)
            defender.ability.active = False

        else:
            # ダメージ修正
            self.modify_damage(atk_idx, move)

            # ダメージ付与
            self.add_hp(def_idx, -self.damage_dealt[atk_idx], move=move)
            self.log[atk_idx].append(f'ダメージ {self.damage_dealt[atk_idx]}')
            self.log[atk_idx].append(f'相手{defender.name} HP {defender.hp}')

            # 被弾回数を記録
            defender.hits_taken += 1

            if defender.hp == 0 and self.get_winner() is not None:  # 勝敗判定
                return

        # 追加効果の処理
        if move.name in PokeDB.move_effect:
            effect = PokeDB.move_effect[move.name]
            target_idx = (effect['object'] + atk_idx) % 2
            r_prob = 2 if attacker.ability == 'てんのめぐみ' else 1

            if (target_idx == atk_idx or self.can_inflict_move_effect(atk_idx, move)) and \
                    self._random.random() < effect['prob'] * r_prob:
                # ランク変動
                if any(effect['rank']):
                    if self.add_rank(target_idx, 0, 0, rank_list=effect['rank']):
                        self.log[atk_idx].insert(-1, '追加効果')

                # 状態異常
                if any(effect['ailment']):
                    candidates = [s for (j, s) in enumerate(PokeDB.ailments) if effect['ailment'][j]]
                    s = self._random.choice(candidates)
                    if self.set_ailment(target_idx, s, badpoison=(effect['ailment'][0] == 2)):
                        self.log[atk_idx].insert(-1, '追加効果')

                # こんらん
                if effect['confusion']:
                    if self.set_condition(target_idx, 'confusion'):
                        self.log[atk_idx].append('追加効果 こんらん')

        # ひるみ判定
        self._flinch = self.check_flinch(atk_idx, move)

        # 技の追加効果
        if move.name in ['アンカーショット', 'かげぬい', 'サイコノイズ', 'しおづけ',
                         'じごくづき', 'なげつける', 'みずあめボム']:
            self.activate_move_effect(atk_idx, move)

        # HP吸収
        if move.name in PokeDB.move_value['drain'] and self.damage_dealt[atk_idx] and \
                self.add_hp(atk_idx, self.get_hp_drain(atk_idx, PokeDB.move_value['drain'][move.name]*self.damage_dealt[atk_idx])):
            self.log[atk_idx].insert(-1, 'HP吸収')

        if self._substituted:
            # みがわりを攻撃したら与ダメージ0を記録
            self.damage_dealt[atk_idx] = 0

        else:
            # 技の追加処理
            if move.name in ['おんねん', 'くちばしキャノン', 'クリアスモッグ', 'コアパニッシャー']:
                self.activate_move_effect(atk_idx, move)

            # 攻撃側の特性
            if attacker.ability.name in PokeDB.ability_category['attack']:
                self.activate_ability(atk_idx, move=move)

            # 防御側の特性
            if defender.ability.name in PokeDB.ability_category['damage'] + PokeDB.ability_category['contact']:
                self.activate_ability(def_idx, move=move)

        # やきつくす判定
        if move == 'やきつくす':
            self.activate_move_effect(atk_idx, move=move)

        # 被弾後に発動するアイテム
        if defender.item.post_hit:
            self.activate_item(def_idx, move)

        # みちづれ判定
        if defender.condition['michizure'] and defender.hp == 0:
            attacker.hp = 0
            self.log[atk_idx].append('瀕死 みちづれ')
            self.move_succeeded[def_idx] = True
            return

        # 反動技
        for s in ['recoil', 'bind']:
            self.activate_move_effect(atk_idx, move, category=s)

        # 追加効果
        if move.name in [
                'わるあがき', 'がんせきアックス', 'キラースピン', 'こうそくスピン', 'ひけん･ちえなみ', 'プラズマフィスト',
                'うちおとす', 'サウザンアロー', 'きつけ', 'くらいつく', 'サウザンウェーブ', 'ついばむ', 'むしくい',
                'とどめばり', 'ドラゴンテール', 'ともえなげ', 'どろぼう', 'ほしがる', 'はたきおとす', 'めざましビンタ',
                'うたかたのアリア', 'ぶきみなじゅもん',
            ] or \
                (move == 'スケイルショット' and combo_count == self.n_strikes):
            self.activate_move_effect(atk_idx, move)

        # 相手のこおり状態解除
        if defender.ailment == 'FLZ' and self.damage_dealt[atk_idx] and \
                (move.type == 'ほのお' or move.name in PokeDB.move_category['unfreeze']):
            self.set_ailment(def_idx)

    def process_status_moves(self, atk_idx: int, move: Move):
        org_def_idx = def_idx = not atk_idx
        attacker, defender = self.pokemon[atk_idx], self.pokemon[def_idx]

        move_class = attacker.eff_move_class(move)

        # マジックミラー判定
        if move_class[-4] == '1' and self.get_defender_ability(def_idx, move) == 'マジックミラー':
            defender.ability.observed = True  # 観測
            self.log[atk_idx].append('マジックミラー')
            self.log[def_idx].append('マジックミラー')
            # 反射 = 攻守入れ替え
            atk_idx, def_idx = def_idx, atk_idx
            attacker, defender = attacker, defender

        # みがわりによる無効判定
        if defender.sub_hp and move_class[-2] != '0':
            self.move_succeeded[atk_idx] = False
            return

        # タイプ相性・特性による無効判定
        if move_class[-3] == '1':
            self.move_succeeded[atk_idx] = bool(self.damage_correction(atk_idx, move))

            if self.get_defender_ability(def_idx, move) == 'おうごんのからだ':
                self.move_succeeded[atk_idx] = False
                defender.ability.observed = True  # 観測

            if not self.move_succeeded[atk_idx]:
                return

        match move.name:
            case 'アクアリング':
                self.move_succeeded[atk_idx] = not attacker.condition['aquaring']
                if self.move_succeeded[atk_idx]:
                    attacker.condition['aquaring'] = 1
            case 'あくまのキッス' | 'うたう' | 'キノコのほうし' | 'くさぶえ' | 'さいみんじゅつ' | 'ダークホール' | 'ねむりごな':
                self.move_succeeded[atk_idx] = self.set_ailment(def_idx, 'SLP', move)
            case 'あくび':
                self.move_succeeded[atk_idx] = self.set_condition(def_idx, 'nemuke', move) and def_idx == org_def_idx
            case 'あさのひざし' | 'こうごうせい' | 'じこさいせい' | 'すなあつめ' | 'タマゴうみ' | 'つきのひかり' | 'なまける' | 'はねやすめ' | 'ミルクのみ':
                r = 0.5
                match move.name:
                    case 'すなあつめ':
                        if self.get_weather() == 'sandstorm':
                            r = 2732/4096
                    case 'あさのひざし' | 'こうごうせい' | 'つきのひかり':
                        match self.get_weather(atk_idx):
                            case 'sunny':
                                r = 0.75
                            case 'rainy' | 'snow' | 'sandstorm':
                                r = 0.25
                self.move_succeeded[atk_idx] = self.add_hp(atk_idx, ut.round_half_down(r*attacker.stats[0]))
                if move == 'はねやすめ' and self.move_succeeded[atk_idx] and not attacker.terastal and 'ひこう' in attacker.types:
                    attacker.lost_types.append('ひこう')
            case 'あまいかおり':
                self.move_succeeded[atk_idx] = bool(self.add_rank(def_idx, 7, -1, by_opponent=True)) and def_idx == org_def_idx
            case 'あまえる':
                self.move_succeeded[atk_idx] = bool(self.add_rank(def_idx, 1, -2, by_opponent=True)) and def_idx == org_def_idx
            case 'あまごい':
                self.move_succeeded[atk_idx] = self.set_weather(atk_idx, 'rainy')
            case 'すなあらし':
                self.move_succeeded[atk_idx] = self.set_weather(atk_idx, 'sandstorm')
            case 'にほんばれ':
                self.move_succeeded[atk_idx] = self.set_weather(atk_idx, 'sunny')
            case 'ゆきげしき':
                self.move_succeeded[atk_idx] = self.set_weather(atk_idx, 'snow')
            case 'あやしいひかり' | 'いばる' | 'おだてる' | 'ちょうおんぱ' | 'てんしのキッス' | 'フラフラダンス':
                self.move_succeeded[atk_idx] = self.set_condition(def_idx, 'confusion')
                match move.name:
                    case 'いばる':
                        self.add_rank(def_idx, 1, +2, by_opponent=True)
                    case 'おだてる':
                        self.add_rank(def_idx, 3, +1, by_opponent=True)
            case 'アロマセラピー' | 'いやしのすず':
                selected = self.selected_pokemons(atk_idx)
                self.move_succeeded[atk_idx] = any([p.ailment for p in selected])
                if self.move_succeeded[atk_idx]:
                    # 場のポケモンの状態異常を回復
                    self.set_ailment(atk_idx)
                    # 控えのポケモンの状態異常を回復
                    for p in selected:
                        if p is not attacker:
                            p.ailment = None
            case 'アンコール':
                self.move_succeeded[atk_idx] = defender.condition['encore'] == 0 and \
                    self.get_defender_ability(def_idx, move) != 'アロマベール' and defender.expended_moves and \
                    (mv := defender.expended_moves[-1]).pp and mv.name not in PokeDB.move_category['non_encore']
                if self.move_succeeded[atk_idx]:
                    defender.condition['encore'] = 3
                    # 相手が後手なら技を変更する
                    if def_idx != self.first_player_idx:
                        self.move[def_idx] = defender.expended_moves[-1]
                    self.move_succeeded[atk_idx] = def_idx == org_def_idx
            case 'いえき' | 'シンプルビーム' | 'なかまづくり' | 'なやみのタネ':
                self.move_succeeded[atk_idx] = not defender.is_ability_protected()
                if self.move_succeeded[atk_idx]:
                    match move.name:
                        case 'いえき':
                            self.move_succeeded[atk_idx] = defender.ability.active
                            defender.ability.active = False
                        case 'シンプルビーム':
                            self.move_succeeded[atk_idx] = defender.ability != 'たんじゅん'
                            defender.ability.name = 'たんじゅん'
                        case 'なかまづくり':
                            self.move_succeeded[atk_idx] = attacker.ability != defender.ability
                            defender.ability.name = attacker.ability.name
                        case 'なやみのタネ':
                            self.move_succeeded[atk_idx] = defender.ability != 'ふみん'
                            defender.ability.name = 'ふみん'
                self.move_succeeded[atk_idx] &= def_idx == org_def_idx
            case 'いたみわけ':
                h = int((self.pokemon[0].hp+self.pokemon[1].hp)/2)
                self.move_succeeded[atk_idx] = h > attacker.hp
                for i in range(2):
                    self.add_hp(i, h - self.pokemon[i].hp, move=move)
            case 'いとをはく' | 'こわいかお' | 'わたほうし':
                self.move_succeeded[atk_idx] = bool(self.add_rank(def_idx, 5, -2, by_opponent=True)) and def_idx == org_def_idx
            case 'いやしのはどう' | 'フラワーヒール':
                r = 0.5
                match move.name:
                    case 'いやしのはどう':
                        if attacker.ability == 'メガランチャー':
                            r = 0.75
                    case 'フラワーヒール':
                        if self.condition['glassfield']:
                            r = 0.75
                self.move_succeeded[atk_idx] = self.add_hp(def_idx, ut.round_half_up(defender.stats[0]*r))
            case 'いやなおと':
                self.move_succeeded[atk_idx] = bool(self.add_rank(def_idx, 2, -2, by_opponent=True)) and def_idx == org_def_idx
            case 'うそなき':
                self.move_succeeded[atk_idx] = bool(self.add_rank(def_idx, 4, -2, by_opponent=True)) and def_idx == org_def_idx
            case 'うつしえ' | 'なりきり':
                self.move_succeeded[atk_idx] = not attacker.is_ability_protected() and \
                    not defender.ability.unreproducible and attacker.ability != defender.ability
                if self.move_succeeded[atk_idx]:
                    attacker.ability.name = defender.ability.name
            case 'うらみ':
                self.move_succeeded[atk_idx] = defender.expended_moves and (mv := defender.expended_moves[-1]) and mv.pp
                if self.move_succeeded[atk_idx]:
                    mv.add_pp(-4)
                    self.log[atk_idx].append(f'{mv} PP {mv.pp}')
            case 'エレキフィールド':
                self.move_succeeded[atk_idx] = self.set_field(atk_idx, 'elecfield')
            case 'グラスフィールド':
                self.move_succeeded[atk_idx] = self.set_field(atk_idx, 'glassfield')
            case 'サイコフィールド':
                self.move_succeeded[atk_idx] = self.set_field(atk_idx, 'psycofield')
            case 'ミストフィールド':
                self.move_succeeded[atk_idx] = self.set_field(atk_idx, 'mistfield')
            case 'えんまく' | 'すなかけ':
                self.move_succeeded[atk_idx] = bool(self.add_rank(def_idx, 6, -1, by_opponent=True)) and def_idx == org_def_idx
            case 'おいかぜ':
                self.move_succeeded[atk_idx] = self.condition['oikaze'][atk_idx] == 0
                if self.move_succeeded[atk_idx]:
                    self.condition['oikaze'][atk_idx] = 4
                    match attacker.ability.name:
                        case 'かぜのり':
                            if self.add_rank(atk_idx, 1, +1):
                                self.log[atk_idx].insert(-1, attacker.ability.name)
                        case 'ふうりょくでんき':
                            if not attacker.condition['charge']:
                                attacker.condition['charge'] = 1
                                self.log[atk_idx].append(f'{attacker.ability} じゅうでん')
            case 'オーロラベール':
                self.move_succeeded[atk_idx] = bool(self.condition['snow']) and self.condition['reflector'][atk_idx] == 0
                if self.move_succeeded[atk_idx]:
                    self.condition['reflector'][atk_idx] = self.condition['lightwall'][atk_idx] = \
                        8 if attacker.item == 'ひかりのねんど' else 5
            case 'おかたづけ' | 'りゅうのまい':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 0, 0, rank_list=[0, 1, 0, 0, 0, 1]))
                if move == 'おかたづけ':
                    for s in ['makibishi', 'dokubishi', 'stealthrock', 'nebanet']:
                        for i in range(2):
                            self.condition[s][i] = 0
            case 'おきみやげ':
                self.move_succeeded[atk_idx] = bool(self.add_rank(def_idx, 0, 0, rank_list=[0, -2, 0, -2], by_opponent=True))
                attacker.hp = 0
            case 'おたけび' | 'なみだめ':
                self.move_succeeded[atk_idx] = \
                    bool(self.add_rank(def_idx, 0, 0, rank_list=[0, -1, 0, -1], by_opponent=True)) and def_idx == org_def_idx
            case 'おにび':
                self.move_succeeded[atk_idx] = self.set_ailment(def_idx, 'BRN', move)
            case 'かいでんぱ':
                self.move_succeeded[atk_idx] = bool(self.add_rank(def_idx, 3, -2, by_opponent=True)) and def_idx == org_def_idx
            case 'かいふくふうじ':
                self.move_succeeded[atk_idx] = defender.condition['healblock'] == 0 and self.get_defender_ability(def_idx, move) != 'アロマベール'
                if self.move_succeeded[atk_idx]:
                    defender.condition['healblock'] = 5
                    self.move_succeeded[atk_idx] = def_idx == org_def_idx
            case 'かえんのまもり' | 'スレッドトラップ' | 'トーチカ' | 'ニードルガード' | 'まもる' | 'みきり':
                self._protect_move = move
            case 'かげぶんしん':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 7, +1))
            case 'かたくなる' | 'からにこもる' | 'まるくなる':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 2, +1))
            case 'かなしばり':
                self.move_succeeded[atk_idx] = defender.condition['kanashibari'] == 0 and \
                    (mv := defender.executed_move) and mv != 'わるあがき' and self.get_defender_ability(def_idx, move) != 'アロマベール'
                if self.move_succeeded[atk_idx]:
                    defender.condition['kanashibari'] = 4
                    self.move_succeeded[atk_idx] = def_idx == org_def_idx
            case 'からをやぶる':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 0, 0, [0, 2, -1, 2, -1, 2]))
            case 'きあいだめ':
                self.move_succeeded[atk_idx] = attacker.condition['critical'] == 0
                if self.move_succeeded[atk_idx]:
                    attacker.condition['critical'] = 2
            case 'ギアチェンジ':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 0, 0, [0, 1, 0, 0, 0, 2]))
            case 'きりばらい':
                self.move_succeeded[atk_idx] = bool(self.add_rank(def_idx, 7, -1, by_opponent=True))
                for s in PokeDB.fields:
                    self.move_succeeded[atk_idx] |= bool(self.condition[s])
                    self.condition[s] = 0
                for s in ['reflector', 'lightwall', 'safeguard', 'whitemist']:
                    self.move_succeeded[atk_idx] |= bool(self.condition[s][def_idx])
                    self.condition[s][def_idx] = 0
                for s in ['makibishi', 'dokubishi', 'stealthrock', 'nebanet']:
                    for i in range(2):
                        self.move_succeeded[atk_idx] |= bool(self.condition[s][i])
                        self.condition[s][i] = 0
                self.move_succeeded[atk_idx] &= def_idx == org_def_idx
            case 'きんぞくおん':
                self.move_succeeded[atk_idx] = bool(self.add_rank(def_idx, 4, -2, by_opponent=True)) and def_idx == org_def_idx
            case 'くすぐる':
                self.move_succeeded[atk_idx] = bool(self.add_rank(def_idx, 0, 0, [0, -1, -1])) and def_idx == org_def_idx
            case 'くろいきり':
                self.move_succeeded[atk_idx] = False
                for i in range(2):
                    self.move_succeeded[atk_idx] |= any(self.pokemon[i].rank)
                    self.pokemon[i].rank = [0]*8
            case 'くろいまなざし' | 'とおせんぼう':
                self.move_succeeded[atk_idx] = not self.is_caught(def_idx)
                if self.move_succeeded[atk_idx]:
                    defender.condition['switchblock'] = 1
                    self.move_succeeded[atk_idx] = self.is_caught(def_idx) and def_idx == org_def_idx
            case 'こうそくいどう' | 'ロックカット':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 5, +2))
            case 'コスモパワー' | 'ぼうぎょしれい':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 0, 0, [0, 0, 1, 0, 1]))
            case 'コットンガード':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 2, +3))
            case 'こらえる':
                self._koraeru = True
                self.move_succeeded[atk_idx] = False  # こらえたときに成功とみなす
            case 'さむいギャグ':
                self.set_weather(atk_idx, 'snow')
            case 'しっぽきり':
                self.move_succeeded[atk_idx] = attacker.sub_hp == 0 and attacker.hp_ratio > 0.5:
                if self.move_succeeded[atk_idx]:
                    self.add_hp(atk_idx, ratio=-0.5)
            case 'しっぽをふる' | 'にらみつける':
                self.move_succeeded[atk_idx] = bool(self.add_rank(def_idx, 2, -1, by_opponent=True)) and def_idx == org_def_idx
            case 'しびれごな' | 'でんじは' | 'へびにらみ':
                self.move_succeeded[atk_idx] = self.set_ailment(def_idx, 'PAR', move)
            case 'じこあんじ':
                self.move_succeeded[atk_idx] = attacker.rank != defender.rank
                if self.move_succeeded[atk_idx]:
                    attacker.rank = defender.rank.copy()
            case 'ジャングルヒール' | 'みかづきのいのり':
                self.move_succeeded[atk_idx] = self.add_hp(atk_idx, ratio=0.25) or self.set_ailment(atk_idx)
            case 'じゅうでん':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 4, +1)) or not attacker.condition['charge']
                attacker.condition['charge'] = 1
            case 'じゅうりょく':
                self.move_succeeded[atk_idx] = self.condition['gravity'] == 0
                if self.move_succeeded[atk_idx]:
                    self.condition['gravity'] = 5
            case 'しょうりのまい':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 0, 0, [0, 1, 1, 0, 0, 1]))
            case 'しろいきり':
                self.move_succeeded[atk_idx] = self.condition['whitemist'][atk_idx] == 0
                if self.move_succeeded[atk_idx]:
                    self.condition['whitemist'][atk_idx] = 5
            case 'しんぴのまもり':
                self.move_succeeded[atk_idx] = self.condition['safeguard'][atk_idx] == 0
                if self.move_succeeded[atk_idx]:
                    self.condition['safeguard'][atk_idx] = 5
            case 'スキルスワップ':
                self.move_succeeded[atk_idx] = not defender.is_ability_protected()
                if self.move_succeeded[atk_idx]:
                    attacker.ability.swap(defender.ability)
                    for i in range(2):
                        self.log[i].append(f'-> {self.pokemon[i].ability}')
                    # 特性の再発動
                    for i in self.speed_order:
                        if self.pokemon[i].ability.immediate:
                            self.activate_ability(i)
            case 'すてゼリフ':
                self.add_rank(def_idx, 0, 0, [0, -1, 0, -1], by_opponent=True)
            case 'すりかえ' | 'トリック':
                self.move_succeeded[atk_idx] = self.pokemon[0].is_item_removable() and self.pokemon[1].is_item_removable()
                if self.move_succeeded[atk_idx]:
                    self.pokemon[0].item, self.pokemon[1].item = self.pokemon[1].item, self.pokemon[0].item
                    for i in range(2):
                        self.log[i].append(f'-> {self.pokemon[i].item}')
            case 'せいちょう':
                v = 2 if self.get_weather(atk_idx) == 'sunny' else 1
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 0, 0, [0, 0, 0, v, v]))
            case 'ステルスロック':
                pre = self.condition['stealthrock'][def_idx]
                self.condition['stealthrock'][def_idx] = 1
                self.move_succeeded[atk_idx] = (self.condition['stealthrock'][def_idx] - pre) > 0
            case 'どくびし':
                pre = self.condition['dokubishi'][def_idx]
                self.condition['dokubishi'][def_idx] = min(2, self.condition['dokubishi'][def_idx] + 1)
                self.move_succeeded[atk_idx] = (self.condition['dokubishi'][def_idx] - pre) > 0
                self.log[atk_idx].append(f"どくびし +{self.condition['dokubishi'][def_idx]}")
            case 'ねばねばネット':
                pre = self.condition['nebanet'][def_idx]
                self.condition['nebanet'][def_idx] = 1
                self.move_succeeded[atk_idx] = (self.condition['nebanet'][def_idx] - pre) > 0
            case 'まきびし':
                pre = self.condition['makibishi'][def_idx]
                self.condition['makibishi'][def_idx] = min(3, self.condition['makibishi'][def_idx] + 1)
                self.move_succeeded[atk_idx] = (self.condition['makibishi'][def_idx] - pre) > 0
                self.log[atk_idx].append(f'まきびし +{self.condition["makibishi"][def_idx]}')
            case 'ソウルビート':
                cost = int(attacker.stats[0]/3)
                self.move_succeeded[atk_idx] = attacker.hp > cost
                if self.move_succeeded[atk_idx]:
                    self.add_hp(atk_idx, -cost)
                    self.add_rank(atk_idx, 0, 0, [0]+[1]*5)
            case 'たくわえる':
                self.move_succeeded[atk_idx] = attacker.condition['stock'] < 3
                if self.move_succeeded[atk_idx]:
                    attacker.condition['stock'] += 1
                    self.add_rank(atk_idx, 0, 0, [0, 0, 1, 0, 1])
            case 'たてこもる' | 'てっぺき' | 'とける':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 2, +2))
            case 'ちいさくなる':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 7, +2))
            case 'ちからをすいとる':
                self.move_succeeded[atk_idx] = defender.rank[1] > -6
                if self.move_succeeded[atk_idx]:
                    self.add_hp(atk_idx, self.get_hp_drain(
                        atk_idx, defender.stats[1] * defender.rank_correction(1)))
                    self.add_rank(def_idx, 1, -1, by_opponent=True)
                    self.move_succeeded[atk_idx] = def_idx == org_def_idx
            case 'ちょうのまい':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 0, 0, [0, 0, 0, 1, 1, 1]))
            case 'ちょうはつ':
                self.move_succeeded[atk_idx] = defender.condition['chohatsu'] == 0 and \
                    self.get_defender_ability(def_idx, move) not in ['アロマベール', 'どんかん']
                if self.move_succeeded[atk_idx]:
                    defender.condition['chohatsu'] = 3
                    self.move_succeeded[atk_idx] = def_idx == org_def_idx
            case 'つぶらなひとみ' | 'なかよくする' | 'なきごえ':
                self.move_succeeded[atk_idx] = \
                    bool(self.add_rank(def_idx, 1, -1, by_opponent=True)) and def_idx == org_def_idx
            case 'つぼをつく':
                indexes = [i for i in range(1, 8) if attacker.rank[i] < 6]
                self.move_succeeded[atk_idx] = bool(indexes)
                if self.move_succeeded[atk_idx]:
                    self.add_rank(atk_idx, self._random.randint(1, 7), +2)
            case 'つめとぎ':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 0, 0, [0, 1, 0, 0, 0, 0, 1]))
            case 'つるぎのまい':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 1, +2))
            case 'テクスチャー':
                self.move_succeeded[atk_idx] = not attacker.terastal
                if self.move_succeeded[atk_idx]:
                    attacker.lost_types += attacker.types
                    attacker.added_types = [attacker.moves[0].type]
                    self.log[atk_idx].append(f'-> {attacker.types[0]}タイプ')
            case 'でんじふゆう':
                self.move_succeeded[atk_idx] = attacker.condition['magnetrise'] == 0
                if self.move_succeeded[atk_idx]:
                    attacker.condition['magnetrise'] = 5
            case 'とおぼえ':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 1, +1))
            case 'どくどく' | 'どくのこな' | 'どくガス' | 'どくのいと':
                if move == 'どくのいと':
                    self.add_rank(def_idx, 5, -1, by_opponent=True)
                self.move_succeeded[atk_idx] = \
                    self.set_ailment(def_idx, 'PSN', move, badpoison=(move == 'どくどく')) and def_idx == org_def_idx
            case 'とぐろをまく':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 0, 0, [0, 1, 1, 0, 0, 0, 1]))
            case 'トリックルーム':
                self.condition['trickroom'] = 5 * (self.condition['trickroom'] == 0)
            case 'ドわすれ':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 4, +2))
            case 'ないしょばなし':
                self.move_succeeded[atk_idx] = bool(self.add_rank(def_idx, 3, -1, by_opponent=True)) and def_idx == org_def_idx
            case 'ねがいごと':
                self.move_succeeded[atk_idx] = self.condition['wish'][atk_idx] == 0
                if self.move_succeeded[atk_idx]:
                    self.condition['wish'][atk_idx] = 2 + 0.001 * int(attacker.stats[0]/2)
                    self.log[atk_idx].append(f"ねがいごと発動")
            case 'ねごと':
                self.move_succeeded[atk_idx] = False
            case 'ねむる':
                self.move_succeeded[atk_idx] = attacker.hp_ratio < 1 and \
                    attacker.condition['healblock'] == 0 and self.set_ailment(atk_idx, 'SLP', move)
                if self.move_succeeded[atk_idx]:
                    attacker.hp = attacker.stats[0]
            case 'ねをはる':
                self.move_succeeded[atk_idx] = not attacker.condition['neoharu']
                if self.move_succeeded[atk_idx]:
                    attacker.condition['neoharu'] = 1
            case 'のろい':
                if 'ゴースト' in attacker.types:
                    self.move_succeeded[atk_idx] = not defender.condition['noroi']
                    if self.move_succeeded[atk_idx]:
                        defender.condition['noroi'] = 1
                        self.add_hp(atk_idx, ratio=-0.5)
                else:
                    self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 0, 0, [0, 1, 1, 0, 0, -1]))
            case 'ハートスワップ':
                self.move_succeeded[atk_idx] = self.pokemon[0].rank != self.pokemon[1].rank
                if self.move_succeeded[atk_idx]:
                    self.pokemon[0].rank, self.pokemon[1].rank = \
                        self.pokemon[1].rank.copy(), self.pokemon[0].rank.copy()
            case 'はいすいのじん':
                self.move_succeeded[atk_idx] = not attacker.condition['switchblock']
                if self.move_succeeded[atk_idx]:
                    attacker.condition['switchblock'] = 1
                    self.move_succeeded[atk_idx] &= bool(self.add_rank(atk_idx, 0, 0, [0]+[1]*5))
            case 'ハバネロエキス':
                self.move_succeeded[atk_idx] = \
                    bool(self.add_rank(def_idx, 0, 0, [0, 2, -2], by_opponent=True)) and def_idx == org_def_idx
            case 'はらだいこ':
                self.move_succeeded[atk_idx] = attacker.hp > (h := int(attacker.stats[0]/2))
                if self.move_succeeded[atk_idx]:
                    self.add_hp(atk_idx, -h)
                    self.move_succeeded[atk_idx] &= bool(self.add_rank(atk_idx, 1, 12))
            case 'ひかりのかべ':
                self.move_succeeded[atk_idx] = self.condition['lightwall'][atk_idx] == 0
                if self.move_succeeded[atk_idx]:
                    self.condition['lightwall'][atk_idx] = 8 if attacker.item == 'ひかりのねんど' else 5
            case 'ひっくりかえす':
                self.move_succeeded[atk_idx] = any(defender.rank)
                if self.move_succeeded[atk_idx]:
                    defender.rank = [-v for v in defender.rank]
                    self.move_succeeded[atk_idx] = def_idx == org_def_idx
                    self.log[atk_idx].append(f'-> {Pokemon.rank2str(defender.rank)}')
            case 'ビルドアップ':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 0, 0, [0, 1, 1]))
            case 'フェザーダンス':
                self.move_succeeded[atk_idx] = \
                    bool(self.add_rank(def_idx, 1, -2, by_opponent=True)) and def_idx == org_def_idx
            case 'ふきとばし' | 'ほえる':
                self.move_succeeded[atk_idx] = self.is_blowable(def_idx)
                if self.move_succeeded[atk_idx]:
                    self.switch_pokemon(def_idx, idx=self._random.choice(self.switchable_indexes(def_idx)))
                    self.move_succeeded[atk_idx] = def_idx == org_def_idx
            case 'ふるいたてる':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 0, 0, [0, 1, 0, 1]))
            case 'ブレイブチャージ' | 'めいそう':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 0, 0, [0, 0, 0, 1, 1]))
                if move == 'ブレイブチャージ':
                    self.set_ailment(atk_idx)
            case 'ほおばる':
                self.move_succeeded[atk_idx] = attacker.item.name[-2:] == 'のみ'
                if self.move_succeeded[atk_idx]:
                    if not self.activate_item(atk_idx):
                        attacker.item.consume()  # 強制消費
                    self.add_rank(atk_idx, 2, +2)
            case 'ほたるび':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 3, +3))
            case 'ほろびのうた':
                for i in range(2):
                    if self.pokemon[i].condition['horobi'] == 0:
                        self.pokemon[i].condition['horobi'] = 4
                self.move_succeeded[atk_idx] = defender.condition['horobi'] == 4 and def_idx == org_def_idx
            case 'まほうのこな' | 'みずびたし':
                t = {'まほうのこな': 'エスパー', 'みずびたし': 'みず'}
                self.move_succeeded[atk_idx] = \
                    not defender.terastal and defender.types != [t[move.name]]
                if self.move_succeeded[atk_idx]:
                    defender.lost_types += defender.types.copy()
                    defender.added_types = [t[move.name]]
            case 'みちづれ':
                attacker.condition['michizure'] = True
            case 'ミラータイプ':
                self.move_succeeded[atk_idx] = not attacker.terastal and attacker.types != defender.types
                if self.move_succeeded[atk_idx]:
                    attacker.lost_types += attacker.types
                    attacker.added_types = defender.types
                    self.log[atk_idx].append(f'-> {attacker.types}タイプ')
            case 'みがわり':
                cost = int(attacker.stats[0]/4)
                self.move_succeeded[atk_idx] = attacker.sub_hp == 0 and attacker.hp > cost
                if self.move_succeeded[atk_idx]:
                    self.add_hp(atk_idx, -cost)
                    attacker.sub_hp = cost
            case 'みをけずる':
                cost = int(attacker.stats[0]/2)
                self.move_succeeded[atk_idx] = \
                    attacker.hp > cost and bool(self.add_rank(atk_idx, 0, 0, [0, 2, 0, 2, 0, 2]))
                if self.move_succeeded[atk_idx]:
                    self.add_hp(atk_idx, -cost)
            case 'メロメロ':
                self.move_succeeded[atk_idx] = \
                    self.set_condition(def_idx, 'meromero') and def_idx == org_def_idx
            case 'もりののろい':
                self.move_succeeded[atk_idx] = not defender.terastal and 'くさ' not in defender.types
                if self.move_succeeded[atk_idx]:
                    defender.added_types.append('くさ')
            case 'やどりぎのタネ':
                self.move_succeeded[atk_idx] = \
                    not defender.condition['yadorigi'] and 'くさ' not in defender.types
                if self.move_succeeded[atk_idx]:
                    defender.condition['yadorigi'] = 1
                    self.move_succeeded[atk_idx] = def_idx == org_def_idx
            case 'リサイクル':
                self.move_succeeded[atk_idx] = not attacker.item.active
                if self.move_succeeded[atk_idx]:
                    attacker.item.active = True
                    self.log[atk_idx].append(f'{attacker.item}回収')
            case 'リフレクター':
                self.move_succeeded[atk_idx] = not self.condition['reflector'][atk_idx]
                if self.move_succeeded[atk_idx]:
                    self.condition['reflector'][atk_idx] = 8 if attacker.item == 'ひかりのねんど' else 5
            case 'リフレッシュ':
                self.move_succeeded[atk_idx] = bool(attacker.ailment)
                if self.move_succeeded[atk_idx]:
                    self.set_ailment(atk_idx)
            case 'ロックオン':
                self.move_succeeded[atk_idx] = not attacker.lockon
                attacker.lockon = True
            case 'わるだくみ':
                self.move_succeeded[atk_idx] = bool(self.add_rank(atk_idx, 3, +2))

    def process_negating_abilities(self, atk_idx: int):
        # マジックミラー判定
        if 'マジックミラー' in self.log[atk_idx]:
            atk_idx = not atk_idx

        def_idx = not atk_idx
        defender = self.pokemon[def_idx]

        for s in ['かんそうはだ', 'ちくでん', 'ちょすい', 'どしょく']:
            if s in self.damage_log[atk_idx]:
                self.damage_log[atk_idx].remove(s)
                defender.ability.observed = True  # 観測
                if self.add_hp(def_idx, ratio=0.25):
                    self.log[def_idx].insert(-1, s)
                break

        for s in ['かぜのり', 'そうしょく']:
            if s in self.damage_log[atk_idx]:
                self.damage_log[atk_idx].remove(s)
                defender.ability.observed = True  # 観測
                if self.add_rank(def_idx, 1, +1):
                    self.log[def_idx].insert(-1, s)
                break

        if 'こんがりボディ' in self.damage_log[atk_idx]:
            self.damage_log[atk_idx].remove('こんがりボディ')
            defender.ability.observed = True  # 観測
            if self.add_rank(def_idx, 2, +2):
                self.log[def_idx].insert(-1, 'こんがりボディ')

        for s in ['ひらいしん', 'よびみず']:
            if s in self.damage_log[atk_idx]:
                self.damage_log[atk_idx].remove(s)
                defender.ability.observed = True  # 観測
                if self.add_rank(def_idx, 3, +1):
                    self.log[def_idx].insert(-1, s)
                    break

        if 'でんきエンジン' in self.damage_log[atk_idx]:
            self.damage_log[atk_idx].remove('でんきエンジン')
            defender.ability.observed = True  # 観測
            if self.add_rank(def_idx, 5, +1):
                self.log[def_idx].insert(-1, 'でんきエンジン')

        if 'もらいび' in self.damage_log[atk_idx]:
            self.damage_log[atk_idx].remove('もらいび')
            defender.ability.count += 1
            defender.ability.observed = True  # 観測

    def calculate_special_damage(self, atk_idx: int, move: Move):
        """ダメージ計算式に従わない技のダメージを計算する"""

        if self.defence_type_correction(atk_idx, move)*self.damage_correction(atk_idx, move) == 0:
            return False

        def_idx = not atk_idx
        attacker, defender = self.pokemon[atk_idx], self.pokemon[def_idx]

        match move.name:
            case 'ぜったいれいど' | 'じわれ' | 'つのドリル' | 'ハサミギロチン':
                if self.get_defender_ability(def_idx, move) != 'がんじょう' or \
                        not (move == 'ぜったいれいど' and 'こおり' in defender.types):
                    self.damage_dealt[atk_idx] = defender.hp
            case 'いかりのまえば' | 'カタストロフィ':
                self.damage_dealt[atk_idx] = int(defender.hp/2)
            case 'カウンター' | 'ミラーコート':
                cls = 'phy' if move == 'カウンター' else 'spe'
                if defender.executed_move and defender.executed_move.cls == cls:
                    self.damage_dealt[atk_idx] = int(self.damage_dealt[def_idx]*2)
            case 'ほうふく' | 'メタルバースト':
                self.damage_dealt[atk_idx] = int(self.damage_dealt[def_idx]*1.5)
            case 'ちきゅうなげ' | 'ナイトヘッド':
                self.damage_dealt[atk_idx] = attacker.level
            case 'いのちがけ':
                self.damage_dealt[atk_idx] = attacker.hp
                attacker.hp = 0
                self.log[atk_idx].append(f'いのちがけ {-self.damage_dealt[atk_idx]}')
            case 'がむしゃら':
                self.damage_dealt[atk_idx] = max(0, defender.hp - attacker.hp)

    def activate_ability(self, player_idx: int, move: Move = None) -> bool:
        opp_idx = not player_idx
        user, opp = self.pokemon[player_idx], self.pokemon[opp_idx]

        activated = False

        # 追加効果扱い
        match user.ability.name * self.can_inflict_move_effect(player_idx, move):
            case 'どくしゅ' | 'どくのくさり':
                bad_poison = True if user.ability.name == 'どくのくさり' else False
                activated = user.is_contact_move(move) and self._random.random() < 0.3 and \
                    self.set_ailment(opp_idx, 'PSN', badpoison=bad_poison)

        match user.ability.name:
            case 'アイスボディ':
                activated = self.get_weather(player_idx) == 'snow' and self.add_hp(player_idx, ratio=0.0625)
            case 'あめうけざら':
                activated = self.get_weather(player_idx) == 'rainy' and self.add_hp(player_idx, ratio=0.0625)
            case 'サンパワー':
                activated = self.get_weather(player_idx) == 'sunny' and self.add_hp(player_idx, ratio=-0.125)
            case 'かんそうはだ':
                sign = {'sunny': -1, 'rainy': +1}
                activated = (s := self.get_weather(player_idx)) in ['sunny', 'rainy'] and \
                    self.add_hp(player_idx, ratio=sign[s]/8)
            case 'あくしゅう':
                if (activated := self._random.random() < 0.1):
                    self._flinch = True
            case 'いかく':
                if opp.ability in PokeDB.ability_category['anti_ikaku']:
                    self.activate_ability(opp_idx)
                    return False
                activated = self.add_rank(opp_idx, 1, -1, by_opponent=True)
            case 'いかりのこうら':
                activated = user.berserk_triggered and self.add_rank(player_idx, 0, 0, [0, 1, -1, 1, -1, 1])
            case 'いかりのつぼ':
                activated = self._critical and self.add_rank(player_idx, 1, +12)
            case 'うのミサイル':
                # TODO うのミサイル実装
                activated = False
            case 'うるおいボディ':
                activated = self.condition['rainy'] and self.set_ailment(player_idx)
            case 'だっぴ':
                activated = self._random.random() < 0.3 and self.set_ailment(player_idx)
            case 'エレキメイカー' | 'ハドロンエンジン':
                activated = self.set_field(player_idx, 'elecfield')
            case 'グラスメイカー':
                activated = self.set_field(player_idx, 'glassfield')
            case 'サイコメイカー':
                activated = self.set_field(player_idx, 'psycofield')
            case 'ミストメイカー':
                activated = self.set_field(player_idx, 'mistfield')
            case 'おもかげやどし':
                d = {'くさ': 5, 'ほのお': 1, 'みず': 4, 'いわ': 2}
                activated = user.types[0] in d and self.add_rank(player_idx, d[user.types[0]], +1)
            case 'かそく':
                activated = user.active_turn and self.add_rank(player_idx, 5, +1)
            case 'かぜのり':
                activated = self.condition['oikaze'][0] and self.add_rank(player_idx, 1, +1)
            case 'かるわざ':
                user.ability.count += 1
                activated = True
            case 'がんじょう':
                activated = self.damage_dealt[opp_idx] == user.stats[0]
                if activated:
                    self.damage_dealt[opp_idx] -= 1
            case 'かんろなみつ':
                self.add_rank(opp_idx, 7, -1)
                activated = True
            case 'カーリーヘアー' | 'ぬめぬめ':
                activated = opp.is_contact_move(move) and self.add_rank(player_idx, 5, -1, by_opponent=True)
            case 'きもったま' | 'せいしんりょく' | 'どんかん' | 'マイペース':
                activated = True
            case 'ぎゃくじょう':
                activated = not user.berserk_triggered and self.add_rank(player_idx, 3, +1)
            case 'クォークチャージ' | 'こだいかっせい':
                s = 'elecfield' if user.ability == 'クォークチャージ' else 'sunny'
                if user.boosted_by == BoostedBy.NONE:
                    # ブースト状態でない場合
                    if self.condition[s]:
                        user.boosted_by = BoostedBy.ABILITY
                    elif user.item == 'ブーストエナジー':
                        self.activate_item(player_idx)
                    else:
                        return False
                else:
                    # ブースト状態の場合
                    if not self.condition[s]:
                        # 外的要因がない場合
                        if user.item == 'ブーストエナジー':
                            self.activate_item(player_idx)
                        else:
                            user.boosted_by = BoostedBy.NONE
                            self.log[player_idx].append("ブースト解除")
                            return False
                    else:
                        return False
                activated = True
                self.log[player_idx].append(f'{PokeDB.stats_label[user.boosted_idx]}上昇')
            case 'くだけるよろい':
                activated = move.cls == 'phy' and self.add_rank(opp_idx, 0, 0, [0, 0, -1, 0, 0, 2])
            case 'こぼれダネ':
                activated = self.set_field(player_idx, 'glassfield')
            case 'さまようたましい' | 'とれないにおい' | 'ミイラ':
                activated = opp.is_contact_move(move) and not user.is_ability_protected()
                if activated:
                    if user.ability.name == 'さまようたましい':
                        user.ability.swap(opp.ability)
                    else:
                        opp.ability.name = user.ability.name
            case 'さめはだ' | 'てつのトゲ':
                activated = opp.is_contact_move(move) and self.add_hp(player_idx, ratio=-0.125)
            case 'じきゅうりょく':
                activated = self.add_rank(player_idx, 2, +1)
            case 'じしんかじょう' | 'しろのいななき' | 'くろのいななき':
                stat_idx = 3 if user.ability == 'くろのいななき' else 1
                activated = opp.hp == 0 and self.add_rank(player_idx, stat_idx, +1)
            case 'しゅうかく':
                activated = user.item.name_lost[-2:] == 'のみ' and \
                    (self.condition['sunny'] or self._random.random() < 0.5)
                if activated:
                    user.item.active = True
            case 'じょうききかん':
                activated = self.get_move_type(player_idx, move) in ['みず', 'ほのお'] and self.add_rank(player_idx, 5, +6)
            case 'すなはき':
                activated = self.set_weather(player_idx, 'sandstorm')
            case 'スロースタート':
                user.ability.count += 1
                if user.ability.count == 5:
                    user.ability.active = False
            case 'せいぎのこころ' | 'ねつこうかん':
                t = 'あく' if opp.ability == 'せいぎのこころ' else 'ほのお'
                activated = self.get_move_type(opp_idx, move) == t and self.add_rank(player_idx, 1, +1)
            case 'せいでんき' | 'どくのトゲ' | 'ほのおのからだ' | 'ほうし':
                ailments = {'せいでんき': 'PAR', 'どくのトゲ': 'PSN', 'ほのおのからだ': 'BRN',
                            'ほうし': self._random.choice(['PSN', 'PAR', 'SLP'])}
                activated = opp.is_contact_move(move) and self._random.random() < 0.3 and \
                    self.set_ailment(player_idx, ailments[user.ability.name])
            case 'ゼロフォーミング':
                count = self.set_weather(player_idx) + self.set_field(player_idx)
                if count:
                    self.log[player_idx].insert(-count, user.ability.name)
                activated = True
            case 'ダウンロード':
                eff_b = int(opp.stats[2]*opp.rank_correction(2))
                eff_d = int(opp.stats[4]*opp.rank_correction(4))
                activated = self.add_rank(player_idx, 1+2*int(eff_b > eff_d), +1)
            case 'でんきにかえる':
                activated = not opp.condition['charge']
                if activated:
                    opp.condition['charge'] = 1
            case 'どくげしょう':
                activated = move.cls == 'phy' and self.condition['dokubishi'][opp_idx] < 2
                if activated:
                    self.condition['dokubishi'][opp_idx] += 1
                    self.log[opp_idx].append(f"どくびし {self.condition['dokubishi'][opp_idx]}")
            case 'ナイトメア':
                activated = opp.ailment == 'SLP' and self.add_hp(opp_idx, ratio=-0.125)
            case 'のろわれボディ':
                activated = not opp.condition['kanashibari'] and opp.expended_moves and self._random.random() < 0.3
                if activated:
                    opp.condition['kanashibari'] = 4
                    self.log[player_idx].append(f'{user.ability} {opp.expended_moves[-1]} かなしばり')
            case 'バリアフリー':
                activated = any(self.condition['reflector'] + self.condition['lightwall'])
                if activated:
                    self.condition['reflector'] = [0]*2
                    self.condition['lightwall'] = [0]*2
            case 'ばんけん':
                activated = self.add_rank(opp_idx, 1, +1, by_opponent=True)
            case 'はんすう':
                activated = True
                user.ability.count += 1
                if user.ability.count == 1:
                    self.log[player_idx].append('開始')
                elif user.ability.count == 3:
                    user.ability.count = 0
                    self.log[player_idx].append('終了')
                    if user.item.name_lost[-2:] == 'のみ':
                        user.item.active = True
                        if not self.activate_item(player_idx):
                            user.item.consume()  # 強制消費
                else:
                    return False
            case 'ひでり' | 'ひひいろのこどう':
                activated = self.set_weather(player_idx, 'sunny')
            case 'あめふらし':
                activated = self.set_weather(player_idx, 'rainy')
            case 'ゆきふらし':
                activated = self.set_weather(player_idx, 'snow')
            case 'すなおこし':
                activated = self.set_weather(player_idx, 'sandstorm')
            case 'びびり':
                activated = self.get_move_type(opp_idx, move) in ['あく', 'ゴースト', 'むし'] and \
                    self.add_rank(player_idx, 5, +1)
            case 'ふうりょくでんき':
                activated = move.name in PokeDB.move_category['wind'] and not user.condition['charge']
                if activated:
                    user.condition['charge'] = 1
            case 'ふくつのこころ':
                activated = self.add_rank(player_idx, 5, +1)
            case 'ふくつのたて':
                self.add_rank(player_idx, 2, +1)
                activated = True
            case 'ふとうのけん':
                self.add_rank(player_idx, 1, +1)
                activated = True
            case 'へんげんじざい' | 'リベロ' | 'へんしょく':
                activated = user.types != [move.type] and move.type != 'ステラ' and not user.terastal
                if move.name in ['へんげんじざい', 'リベロ']:
                    activated &= user.ability.count == 0
                if activated:
                    user.lost_types += user.types
                    user.added_types += [move.type]
                    user.ability.count = 1
                    self.log[player_idx].append(f'-> {move.type}タイプ')
            case 'ポイズンヒール':
                # 毒ダメージを受けない = 特性が発動している
                if (activated := user.ailment == 'PSN'):
                    self.add_hp(player_idx, ratio=0.125)
            case 'ほおぶくろ':
                activated = self.add_hp(player_idx, ratio=1/3)
            case 'ほろびのボディ':
                for i in range(2):
                    if not self.pokemon[i].condition['hotobi']:
                        self.pokemon[i].condition['hotobi'] = 4
                        activated = True
            case 'マジシャン':
                activated = not user.item.active and opp.item and opp.is_item_removable()
                if activated:
                    user.item.name = opp.item.name
                    opp.item.active = False
            case 'みずがため':
                activated = self.get_move_type(player_idx, move) == 'みず' and self.add_rank(player_idx, 2, +2)
            case 'ムラっけ':
                up_idxs = [i for i in range(1, 6) if user.rank[i] < 6]
                if (activated := any(up_idxs)):
                    # 能力上昇
                    up_idx = self._random.choice(up_idxs)
                    self.add_rank(player_idx, up_idx, +2)
                    down_idxs = [i for i in range(1, 6) if user.rank[i] > -6 and i != up_idx]
                    # 能力下降
                    if down_idxs:
                        self.add_rank(player_idx, self._random.choice(down_idxs), -1)
            case 'メロメロボディ':
                activated = self._random.random() < 0.3 and self.set_condition(opp_idx, 'meromero')
            case 'ゆうばく':
                activated = user.hp == 0 and self.add_hp(opp_idx, ratio=-0.25)
            case 'わたげ':
                activated = self.add_rank(player_idx, 5, -1)

        if activated:
            self.log[player_idx].insert(-1, user.ability.name)
            user.ability.observed = True  # 観測
            if user.ability.name in PokeDB.ability_category['one_time']:
                user.ability.active = False
            return True

        return False

    def activate_item(self, player_idx: int, move: Move = None) -> bool:
        opp_idx = not player_idx
        user, opp = self.pokemon[player_idx], self.pokemon[opp_idx]

        if not user.item.active:
            return False

        activated = False
        r_fruit = 2 if user.ability == 'じゅくせい' else 1

        # 瀕死でも発動するアイテム
        match user.item.name:
            case 'ゴツゴツメット':
                activated = not self._substituted and opp.is_contact_move(move) and \
                    self.add_hp(opp_idx, ratio=-1/6)
            case 'ふうせん':
                activated = True
            case 'ジャポのみ' | 'レンブのみ':
                cls = 'phy' if user.item == 'ジャポのみ' else 'spe'
                activated = not self.is_nervous(player_idx) and move.cls == cls and \
                    self.add_hp(opp_idx, ratio=-r_fruit/8)

        # 瀕死でないならば発動するアイテム
        match user.item.name * bool(user.hp):
            case 'いのちのたま':
                activated = self.add_hp(player_idx, ratio=-0.1)
            case 'かいがらのすず':
                activated = self.add_hp(player_idx, int(self.damage_dealt[player_idx]/8))
            case 'かえんだま':
                activated = self.set_ailment(player_idx, 'BRN', safeguard=False)
            case 'どくどくだま':
                activated = self.set_ailment(player_idx, 'PSN', badpoison=True, safeguard=False)
            case 'エレキシード' | 'グラスシード':
                s = 'elecfield' if user.item == 'エレキシード' else 'glassfield'
                activated = self.condition[s] and self.add_rank(player_idx, 2, +1)
            case 'サイコシード' | 'ミストシード':
                s = 'psycofield' if user.item == 'エレキシード' else 'mistfield'
                activated = self.condition[s] and self.add_rank(player_idx, 4, +1)
            case 'おうじゃのしるし' | 'するどいキバ':
                activated = self._random.random() < 0.1 * (2 if user.ability == 'てんのめぐみ' else 1)
                if activated:
                    self._flinch = True
            case 'からぶりほけん':
                activated = move and move.name not in PokeDB.move_category['one_ko'] and \
                    self.add_rank(player_idx, 5, +2)
            case 'きあいのタスキ':
                activated = self.damage_dealt[opp_idx] == user.stats[0]
                if activated:
                    self.damage_dealt[opp_idx] -= 1
            case 'きあいのハチマキ':
                activated = self.damage_dealt[opp_idx] == user.hp
                if activated:
                    self.damage_dealt[opp_idx] -= 1
            case 'きゅうこん' | 'ひかりごけ':
                activated = not self._substituted and move.type == 'みず' and self.add_rank(player_idx, 3, +1)
            case 'じゅうでんち' | 'ゆきだま':
                t = 'でんき' if user.item.name == 'じゅうでんち' else 'こおり'
                activated = not self._substituted and move.type == t and self.add_rank(player_idx, 1, +1)
            case 'たべのこし' | 'くろいヘドロ':
                sign = -1 if user.item.name == 'くろいヘドロ' and 'どく' not in user.types else 1
                activated = self.add_hp(player_idx, ratio=sign/16)
            case 'じゃくてんほけん':
                activated = not self._substituted and \
                    self.defence_type_correction(player_idx, move) > 1 and self.add_rank(player_idx, 0, 0, [0, 2, 0, 2])
            case 'しろいハーブ':
                activated = any([v < 0 for v in user.rank])
                if activated:
                    user.rank = [max(0, v) for v in user.rank]
            case 'せんせいのツメ':
                activated = self._random.random() < 0.2
            case 'だっしゅつボタン':
                activated = self.damage_dealt[opp_idx] and self.switchable_indexes(player_idx)
            case 'のどスプレー':
                activated = move.name in PokeDB.move_category['sound'] and self.add_rank(player_idx, 3, +1)
            case 'パワフルハーブ':
                if (activated := user.unresponsive_turn > 0):
                    user.unresponsive_turn = 0
                    self.log[player_idx].append('溜め省略')
            case 'ブーストエナジー':
                activated = True
                user.boosted_by = BoostedBy.ITEM
            case 'メンタルハーブ':
                for s in ['meromero', 'encore', 'kanashibari', 'chohatsu', 'healblock']:
                    if user.condition[s]:
                        user.condition[s] = 0
                        self.log[player_idx].append(f'{PokeDB.JPN[s]}解除')
                        activated = True
            case 'ものまねハーブ':
                activated = True
            case 'ルームサービス':
                activated = self.condition['trickroom'] and self.add_rank(player_idx, 5, -1)
            case 'レッドカード':
                if (activated := self.is_blowable(opp_idx)):
                    self.switch_pokemon(opp_idx)

        match user.item.name * (not self.is_nervous(player_idx)):
            case 'イバンのみ':
                activated = user.hp_ratio <= (0.5 if user.ability == 'くいしんぼう' else 0.25)
            case 'オレンのみ':
                activated = not user.condition['healblock'] and self.add_hp(player_idx, 10*r_fruit)
            case 'オボンのみ' | 'ナゾのみ':
                if user.item == 'ナゾのみ':
                    activated = self.defence_type_correction(player_idx, move) > 1
                else:
                    activated = True
                activated &= not user.condition['healblock'] and self.add_hp(player_idx, ratio=r_fruit/4)
            case 'フィラのみ' | 'ウイのみ' | 'マゴのみ' | 'バンジのみ' | 'イアのみ':
                activated = not user.condition['healblock'] and self.add_hp(player_idx, ratio=r_fruit/3)
            case 'ヒメリのみ':
                for move in user.moves:
                    if not move.pp:
                        move.add_pp(10)
                        activated = True
                        break
            case 'カゴのみ':
                activated = user.ailment == 'SLP' and self.set_ailment(player_idx)
            case 'クラボのみ':
                activated = user.ailment == 'PAR' and self.set_ailment(player_idx)
            case 'チーゴのみ':
                activated = user.ailment == 'BRN' and self.set_ailment(player_idx)
            case 'ナナシのみ':
                activated = user.ailment == 'FLZ' and self.set_ailment(player_idx)
            case 'モモンのみ':
                activated = user.ailment == 'PSN' and self.set_ailment(player_idx)
            case 'ラムのみ':
                activated = user.ailment and self.set_ailment(player_idx)
            case 'キーのみ':
                if (activated := user.condition['confusion']):
                    user.condition['confusion'] = 0
                    self.log[player_idx].append(f'こんらん解除')
            case 'チイラのみ':
                activated = user.hp_ratio <= (0.5 if user.ability == 'くいしんぼう' else 0.25) and \
                    self.add_rank(player_idx, 1, r_fruit)
            case 'リュガのみ' | 'アッキのみ':
                activated = user.hp_ratio <= (0.5 if user.ability == 'くいしんぼう' else 0.25) and \
                    self.add_rank(player_idx, 2, r_fruit)
            case 'ヤタピのみ':
                activated = user.hp_ratio <= (0.5 if user.ability == 'くいしんぼう' else 0.25) and \
                    self.add_rank(player_idx, 3, r_fruit)
            case 'ズアのみ' | 'タラプのみ':
                activated = user.hp_ratio <= (0.5 if user.ability == 'くいしんぼう' else 0.25) and \
                    self.add_rank(player_idx, 4, r_fruit)
            case 'カムラのみ':
                activated = user.hp_ratio <= (0.5 if user.ability == 'くいしんぼう' else 0.25) and \
                    self.add_rank(player_idx, 5, r_fruit)
            case 'サンのみ':
                if (activated := user.condition['critical'] == 0):
                    user.condition['critical'] = 2
                    self.log[player_idx].append("急所ランク+2")
            case 'スターのみ':
                activated = self.add_rank(player_idx, self._random.choice([i for i in range(1, 6) if user.rank[i] < 6]), r_fruit)
            case 'アッキのみ':
                activated = move and move.cls == 'phy' and self.add_rank(player_idx, 2, +1)
            case 'タラプのみ':
                activated = move and move.cls == 'spe' and self.add_rank(player_idx, 4, +1)

        if not activated:
            return False

        if user.item.name[-2:] == 'のみ' and user.ability.name in PokeDB.ability_category['fruit']:
            self.activate_ability(player_idx)

        # アイテム消費
        if user.item.consumable:
            user.item.consume()
            self.log[player_idx].append(f'{user.item.name_lost}消費')
            if user.ability == 'かるわざ':
                self.activate_ability(player_idx)
        else:
            self.log[player_idx].append(f'{user.item.name}発動')
            user.item.observed = True  # 観測

        return True

    def activate_move_effect(self, atk_idx: int, move: Move, category: str = None) -> bool:
        """
        攻撃技の追加効果・処理を発動する

        Parameters
        ----------
        atk_idx : int
            技を使用した側のプレイヤーインデックス
        move : Move
            技
        category : str, optional
            技の分類, by default None

        Returns
        -------
        bool
            追加効果・処理が発動したらTrue
        """

        def_idx = not atk_idx
        attacker = self.pokemon[atk_idx]
        defender = self.pokemon[def_idx]

        # 技の分類ごとの追加処理
        if category and move.name in PokeDB.move_category[category]:
            match category:
                case 'bind':
                    if not defender.condition['bind'] and not self._substituted:
                        turn = 7 if attacker.item == 'ねばりのかぎづめ' else 5
                        ratio = 6 if attacker.item == 'しめつけバンド' else 8
                        defender.condition['bind'] = turn + 0.1 * ratio
                        return True
                case 'cost':
                    # 発動コスト
                    cost = ut.round_half_up(attacker.stats[0] * PokeDB.move_value['cost'][move.name])
                    if self.add_hp(atk_idx, -cost):
                        self.log[atk_idx].insert(-1, '反動')
                        return True
                case 'immovable':
                    # 反動で動けない技
                    self.pokemon[atk_idx].unresponsive_turn = 1
                    return True
                case 'mis_recoil':
                    # 技の失敗による反動
                    if self.add_hp(atk_idx, ratio=-PokeDB.move_value['mis_recoil'][move.name]):
                        self.log[atk_idx].insert(-1, '反動')
                        return True
                case 'rage':
                    if attacker.unresponsive_turn == 0:
                        # あばれる状態の付与
                        attacker.unresponsive_turn = self._random.randint(1, 2)
                    else:
                        # ターン経過
                        attacker.unresponsive_turn -= 1
                        # こんらん付与
                        if self.set_condition(atk_idx, 'confusion'):
                            self.log[atk_idx].append(f'{move}解除 こんらん')
                    self.log[atk_idx].append(f'{move} 残り{attacker.unresponsive_turn}ターン')
                    return True
                case 'recoil':
                    # 反動
                    if self.damage_dealt[atk_idx] and attacker.ability != 'いしあたま':
                        recoil = ut.round_half_up(self.damage_dealt[atk_idx] * PokeDB.move_value['recoil'][move.name])
                        if self.add_hp(atk_idx, -recoil):
                            self.log[atk_idx].insert(-1, '反動')
                            return True
                case 'wall_break':
                    # 壁破壊
                    if self.damage_dealt[atk_idx] and self.condition['reflector'][def_idx] + self.condition['lightwall'][def_idx]:
                        self.condition['reflector'][def_idx] = self.condition['lightwall'][def_idx] = 0
                        self.log[atk_idx].append('壁破壊')
                        return True

            return False

        # 追加効果 (相手に付与)
        match move.name * self.can_inflict_move_effect(atk_idx, move):
            case 'アンカーショット' | 'かげぬい':
                if not defender.condition['switchblock']:
                    defender.condition['switchblock'] = 1
                    self.log[atk_idx].append('追加効果 にげられない')
                    return True
            case 'うたかたのアリア':
                if defender.ailment == 'BRN':
                    self.set_ailment(def_idx)
                    self.log[atk_idx].append('追加効果 やけど解除')
                    return True
            case 'ぶきみなじゅもん':
                if defender.expended_moves and (mv := defender.expended_moves[-1]).pp:
                    mv.add_pp(-3)
                    self.log[atk_idx].append(f'追加効果 {mv} PP {mv.pp}')
                    return True
            case 'うちおとす' | 'サウザンアロー':
                if self.is_float(def_idx):
                    defender.condition['anti_air'] = 1
                    self.log[atk_idx].append('追加効果 うちおとす')
                    return True
            case 'エレクトロビーム' | 'メテオビーム':
                if self.add_rank(atk_idx, 3, +1):
                    return True
            case 'ロケットずつき':
                if self.add_rank(atk_idx, 2, +1):
                    return True
            case 'きつけ':
                if defender.ailment == 'PAR':
                    self.set_ailment(def_idx)
                    self.log[atk_idx].append('追加効果 まひ解除')
                    return True
            case 'くらいつく':
                if all(not p.condition['switchblock'] and 'ゴースト' not in p.types for p in self.pokemon):
                    for j in range(2):
                        self.pokemon[j].condition['switchblock'] = 1
                    self.log[atk_idx].append('追加効果 くらいつく')
                    return True
            case 'サイコノイズ':
                if defender.condition['healblock'] == 0:
                    defender.condition['healblock'] = 2
                    self.log[atk_idx].append('追加効果 かいふくふうじ')
                    return True
            case 'サウザンウェーブ':
                if not defender.condition['switchblock']:
                    defender.condition['switchblock'] = 1
                    self.log[atk_idx].append('追加効果 にげられない')
                    return True
            case 'しおづけ':
                if not defender.condition['shiozuke']:
                    defender.condition['shiozuke'] = 1
                    self.log[atk_idx].append('追加効果 しおづけ')
                    return True
            case 'じごくづき':
                if defender.condition['jigokuzuki'] == 0:
                    defender.condition['jigokuzuki'] = 2
                    self.log[atk_idx].append('追加効果 じごくづき')
                    return True
            case 'なげつける':
                match attacker.item.name:
                    case 'おうじゃのしるし' | 'するどいキバ':
                        self._flinch = self.can_be_flinched(def_idx)
                        if self._flinch:
                            self.log[atk_idx].append('追加効果 ひるみ')
                    case 'かえんだま':
                        if self.set_ailment(def_idx, 'BRN', move):
                            self.log[atk_idx].insert(-1, '追加効果')
                    case 'でんきだま':
                        if self.set_ailment(def_idx, 'PAR', move):
                            self.log[atk_idx].insert(-1, '追加効果')
                    case 'どくバリ':
                        if self.set_ailment(def_idx, 'PSN', move):
                            self.log[atk_idx].insert(-1, '追加効果')
                    case 'どくどくだま':
                        if self.set_ailment(def_idx, 'PSN', move, badpoison=True):
                            self.log[atk_idx].insert(-1, '追加効果')
                # アイテム消失
                attacker.item.active = False
                attacker.item.observed = True  # 観測
                self.log[atk_idx].append(f'{attacker.item.name_lost}消失')
                return True
            case 'みずあめボム':
                if defender.condition['ame_mamire'] == 0:
                    defender.condition['ame_mamire'] = 3
                    self.log[atk_idx].append('追加効果 あめまみれ')
                    return True

        # 追加効果/処理 (みがわりにより無効)
        match move.name * (not self._substituted):
            case 'クリアスモッグ':
                if any(defender.rank):
                    defender.rank = [0]*8
                    self.log[atk_idx].append('追加効果 ランクリセット')
                    return True
            case 'ついばむ' | 'むしくい':
                if defender.item.name[-2:] == 'のみ':
                    self.log[atk_idx].append('追加効果')
                    backup = attacker.item
                    attacker.item = defender.item
                    self.activate_item(atk_idx)
                    attacker.item = backup
                    return True
            case 'ドラゴンテール' | 'ともえなげ':
                if self.is_blowable(def_idx):
                    self.switch_pokemon(def_idx, idx=self._random.choice(self.switchable_indexes(def_idx)))
                    return True
            case 'どろぼう' | 'ほしがる':
                if not attacker.item and defender.item and defender.is_item_removable():
                    attacker.item = Item(defender.item.name)
                    attacker.item.observed = True
                    defender.item.active = False
                    self.log[atk_idx].append(f'追加効果 {attacker.item}奪取')
                    return True
            case 'はたきおとす':
                if defender.item.name:
                    defender.item.active = False
                    self.log[atk_idx].append(f'追加効果 {defender.item.name_lost}消失')
                    return True
            case 'めざましビンタ':
                if defender.ailment == 'SLP':
                    self.set_ailment(def_idx)
                    self.log[atk_idx].append('追加効果 ねむり解除')
                    return True
            case 'やきつくす':
                if defender.item.name[-2:] == 'のみ' or defender.item.name[-4:] == 'ジュエル':
                    defender.item.consume()
                    self.log[atk_idx].append(f'追加効果 {defender.item.name_lost}消失')
                    return True

        # 追加効果/処理　(その他)
        match move.name:
            case 'アイアンローラー' | 'アイススピナー':
                if (field := self.get_field()):
                    self.set_field(0)
                    self.log[atk_idx].append(f'追加効果 {PokeDB.JPN[field]}消滅')
                    return True
            case 'おんねん':
                pass  # TODO おんねん実装
            case 'かえんのまもり':
                if self.set_ailment(atk_idx, 'BRN'):
                    self.log[atk_idx].insert(-1, '追加効果')
                    return True
            case 'スレッドトラップ':
                if self.add_rank(atk_idx, 5, -1, by_opponent=True):
                    self.log[atk_idx].insert(-1, '追加効果')
                    return True
            case 'トーチカ':
                if self.set_ailment(atk_idx, 'PSN'):
                    self.log[atk_idx].insert(-1, '追加効果')
                    return True
            case 'ニードルガード':
                if self.add_hp(atk_idx, ratio=-0.125):
                    self.log[atk_idx].insert(-1, '追加効果')
                    return True
            case 'がんせきアックス':
                if self.condition['stealthrock'][def_idx] == 0:
                    self.condition['stealthrock'][def_idx] = 1
                    self.log[atk_idx].append('追加効果 ステルスロック')
                    return True
            case 'ひけん･ちえなみ':
                if self.condition['makibishi'][def_idx] < 3:
                    self.condition['makibishi'][def_idx] = min(3, self.condition['makibishi'][def_idx]+1)
                    self.log[atk_idx].append(f"追加効果 まきびし {self.condition['makibishi'][def_idx]}")
                    return True
            case 'キラースピン' | 'こうそくスピン':
                removed = []
                for s in ['yadorigi', 'bind']:
                    if attacker.condition[s]:
                        attacker.condition[s] = 0
                        removed.append(s)
                for s in ['makibishi', 'dokubishi', 'stealthrock', 'nebanet']:
                    if self.condition[s][atk_idx]:
                        self.condition[s][atk_idx] = 0
                        removed.append(s)
                if removed:
                    self.log[atk_idx].append(f'追加効果 {[PokeDB.JPN[s] for s in removed]}解除')
                    return True
            case 'くちばしキャノン':
                pass  # TODO くちばしキャノン実装
            case 'コアパニッシャー':
                if atk_idx != self.first_player_idx and not defender.ability.protected:
                    self.log[atk_idx].append(f'追加効果 {defender.ability}消失')
                    defender.ability.active = False
                    return True
            case 'スケイルショット':
                if self.add_rank(atk_idx, 0, 0, rank_list=[0, 0, -1, 0, 0, 1]):
                    self.log[atk_idx].insert(-1, '追加効果')
                    return True
            case 'テラバースト':
                if attacker.terastal == 'ステラ' and attacker.terastal and \
                        self.add_rank(atk_idx, 0, 0, rank_list=[0, -1, 0, -1]):
                    self.log[atk_idx].insert(-1, '追加効果')
                    return True
            case 'でんこうそうげき' | 'もえつきる':
                t = {'でんこうそうげき': 'でんき', 'もえつきる': 'ほのお'}
                self.pokemon[atk_idx].lost_types.append(t[move.name])
                self.log[atk_idx].append(f'追加効果 {t[move.name]}タイプ消失')
                return True
            case 'とどめばり':
                if defender.hp == 0 and self.add_rank(atk_idx, 1, +3):
                    self.log[atk_idx].insert(-1, '追加効果')
                    return True
            case 'わるあがき':
                self.add_hp(atk_idx, -ut.round_half_up(attacker.stats[0]/4), move=move)
                self.log[atk_idx].insert(-1, '反動')
                return True

        return False

    def check_flinch(self, atk_idx: int, move: Move) -> bool:
        """相手をひるませたらTrueを返す"""
        if not self.can_be_flinched(not atk_idx):
            return False

        attacker = self.pokemon[atk_idx]

        if move.name in PokeDB.move_effect and (prob := PokeDB.move_effect[move.name]['flinch']):
            prob *= 2 if attacker.ability == 'てんのめぐみ' else 1
            if self._random.random() < prob:
                self.log[atk_idx].append('追加効果 ひるみ')
                return True

        elif self.can_inflict_move_effect(atk_idx, move):
            # 技以外のひるみ判定
            if attacker.ability == 'あくしゅう' and self.activate_ability(atk_idx):
                self.log[atk_idx].append('追加効果 ひるみ')
                return True
            elif attacker.item.name in ['おうじゃのしるし', 'するどいキバ'] and self.activate_item(atk_idx):
                self.log[atk_idx].append('追加効果 ひるみ')
                return True

        return False

    def did_protect_succeed(self, atk_idx: int, move: Move) -> bool:
        """
        まもる系の技の処理を行い、まもるが成功したらTrueを返す

        Parameters
        ----------
        atk_idx : int
            攻撃側のプレイヤーインデックス
        move : Move
            攻撃技

        Returns
        ----------
        bool
            まもるが成功したらTrue
        """

        if not self._protect_move:
            return False

        def_idx = not atk_idx
        attacker, defender = self.pokemon[atk_idx], self.pokemon[def_idx]

        # まもる貫通
        if move.name in PokeDB.move_category['anti_protect'] or \
                (attacker.ability == 'ふかしのこぶし' and attacker.is_contact_move(move)):
            self.move_succeeded[def_idx] = False
            return False

        move_class = attacker.eff_move_class(move)

        self.move_succeeded[def_idx] = move_class in ['phy', 'spe']

        if self._protect_move != 'かえんのまもり':
            self.move_succeeded[def_idx] |= move_class[-1] == '1'

        # まもる成功
        if self.move_succeeded[def_idx]:
            # 接触時の追加効果
            if attacker.is_contact_move(move):
                self.activate_move_effect(def_idx, move=self._protect_move)

            # 攻撃失敗による反動
            self.activate_move_effect(atk_idx, move=move, category='mis_recoil')

            self.pokemon[atk_idx].unresponsive_turn = 0
            self.log[atk_idx].append(f'{self._protect_move}で防がれた')
            self.log[def_idx].append(f'{self._protect_move}成功')

            return True

    def on_miss(self, atk_idx: int, move):
        """技が外れたときの処理"""
        self.log[atk_idx].append('はずれ')
        self.pokemon[atk_idx].unresponsive_turn = 0
        self.move_succeeded[atk_idx] = False

        # 反動
        self.activate_move_effect(atk_idx, move, category='mis_recoil')

        # からぶりほけん判定
        if self.activate_item(atk_idx, 'からぶりほけん', move=move):
            # からぶりほけんが発動したら技は成功したとみなす
            self.move_succeeded[atk_idx] = True

    def consume_stellar_type(self, player_idx: int, move: Move) -> str:
        """このターンに消費されたステラ強化タイプを返す"""
        if self.damage_dealt[player_idx] and self.pokemon[player_idx].terastal == 'ステラ' and \
                self.pokemon[player_idx].terastal and move.type in self.stellar[player_idx] and \
            'テラパゴス' not in self.pokemon[player_idx].name:
            self.stellar[player_idx].remove(move.type)
            self.log[player_idx].append(f"ステラ {move.type}消費")

    def process_turn_end(self):
        """
        ターン終了時の処理を行う。
        """
        if self.get_winner() is not None:  # 勝敗判定
            return

        # 天候カウント
        for s in PokeDB.weathers:
            if self.condition[s]:
                self.condition[s] -= 1
                for i in range(2):
                    self.log[i].append(f'{PokeDB.JPN[s]} 残り{self.condition[s]}ターン')
                break

        # 砂嵐ダメージ
        if self.get_weather() == 'sandstorm':
            for pidx in self.speed_order:
                p = self.pokemon[pidx]

                if p.hp == 0 or any(s in p.types for s in ['いわ', 'じめん', 'はがね']) or \
                    p.ability.name in ['すなかき', 'すながくれ', 'すなのちから'] or self.is_overcoat(pidx) or \
                        (p.hidden and p.executed_move.name in ['あなをほる', 'ダイビング']):
                    continue

                if self.add_hp(pidx, ratio=-0.0625):
                    self.log[pidx].insert(-1, 'すなあらし')
                    # 勝敗判定
                    if self.get_winner() is not None:
                        return

        # 天候に関する特性
        for pidx in self.speed_order:
            p = self.pokemon[pidx]

            if p.hp == 0 or \
                    (p.hidden and p.executed_move.name in ['あなをほる', 'ダイビング']):
                continue

            if p.ability.name in ['かんそうはだ', 'サンパワー', 'あめうけざら', 'アイスボディ']:
                self.activate_ability(pidx)

                # 勝敗判定
                if self.get_winner() is not None:
                    return

        # ねがいごと
        for pidx in self.speed_order:
            if self.condition['wish'][pidx]:
                # カウント
                self.condition['wish'][pidx] -= 1
                self.log[pidx].append(f"ねがいごと 残り{int(self.condition['wish'][pidx])}ターン")
                # 回復
                if int(self.condition['wish'][pidx]) == 0:
                    self.add_hp(pidx, 1000*ut.frac(self.condition['wish'][pidx]))
                    self.condition['wish'][pidx] = 0

        # グラスフィールド回復
        if self.condition['glassfield']:
            for pidx in self.speed_order:
                if p.hidden and p.executed_move.name in ['あなをほる', 'ダイビング']:
                    continue
                if self.pokemon[pidx].hp and not self.is_float(pidx) and \
                        self.add_hp(pidx, ratio=0.0625):
                    self.log[pidx].insert(-1, 'グラスフィールド')

        # うるおいボディ等
        for pidx in self.speed_order:
            p = self.pokemon[pidx]

            if p.ailment and p.hp and p.ability.name in ['うるおいボディ', 'だっぴ']:
                self.activate_ability(pidx)

        # たべのこし
        for pidx in self.speed_order:
            p = self.pokemon[pidx]

            if p.hp and p.item.name in ['たべのこし', 'くろいヘドロ']:
                self.activate_item(pidx)
                # 勝敗判定
                if self.get_winner() is not None:
                    return

        # アクアリング・ねをはる
        for pidx in self.speed_order:
            p = self.pokemon[pidx]

            if p.hp == 0:
                continue

            h = self.get_hp_drain(pidx, int(p.stats[0]/16), from_opponent=False)
            for s in ['aquaring', 'neoharu']:
                if p.condition[s] and self.add_hp(pidx, h):
                    self.log[pidx].insert(-1, s)

        # やどりぎのタネ
        for pidx in self.speed_order:
            p1 = self.pokemon[pidx]
            p2 = self.pokemon[not pidx]

            if p1.condition['yadorigi'] and (p1.hp * p2.hp):
                h = min(p1.hp, int(p1.stats[0]/16))
                # ダメージ処理
                if self.add_hp(pidx, -h):
                    self.log[pidx].insert(-1, 'やどりぎのタネ')
                    # 勝敗判定
                    if self.get_winner() is not None:
                        return
                    # 回復処理
                    if self.add_hp(not pidx, self.get_hp_drain(not pidx, h)):
                        self.log[not pidx].insert(-1, 'やどりぎのタネ')
                        # 勝敗判定
                        if self.get_winner() is not None:
                            return

        # 状態異常ダメージ
        for pidx in self.speed_order:
            p = self.pokemon[pidx]

            if p.hp == 0:
                continue

            match p.ailment:
                case 'PSN':
                    if p.ability == 'ポイズンヒール' and self.activate_ability(pidx):
                        pass
                    elif p.condition['badpoison']:
                        if self.add_hp(pidx, ratio=-p.condition['badpoison']/16):
                            self.log[pidx].insert(-1, 'もうどく')
                            # 勝敗判定
                            if self.get_winner() is not None:
                                return
                    elif self.add_hp(pidx, ratio=-0.125):
                        self.log[pidx].insert(-1, 'どく')
                        # 勝敗判定
                        if self.get_winner() is not None:
                            return

                    # もうどくカウント
                    if p.condition['badpoison']:
                        p.condition['badpoison'] += 1

                case 'BRN':
                    if self.add_hp(pidx, ratio=(-0.03125 if p.ability == 'たいねつ' else 0.0625)):
                        self.log[pidx].insert(-1, 'やけど')
                        # 勝敗判定
                        if self.get_winner() is not None:
                            return

        # 呪いダメージ
        for pidx in self.speed_order:
            p = self.pokemon[pidx]

            if p.hp and p.condition['noroi'] and self.add_hp(pidx, ratio=-0.25):
                self.log[pidx].insert(-1, '呪い')
                # 勝敗判定
                if self.get_winner() is not None:
                    return

        # バインドダメージ
        for pidx in self.speed_order:
            p = self.pokemon[pidx]

            if p.hp and p.condition['bind']:
                p.condition['bind'] -= 1
                self.log[pidx].append(f"バインド 残り{int(p.condition['bind'])}ターン")

                if self.add_hp(pidx, ratio=-0.1/ut.frac(p.condition['bind'])):
                    self.log[pidx].insert(-1, 'バインド')
                    # 勝敗判定
                    if self.get_winner() is not None:
                        return

                if int(p.condition['bind']) == 0:
                    p.condition['bind'] = 0

        # しおづけダメージ
        for pidx in self.speed_order:
            p = self.pokemon[pidx]

            if p.hp and p.condition['shiozuke']:
                r = 2 if any(t in p.types for t in ['みず', 'はがね']) else 1
                if self.add_hp(pidx, ratio=-r/8):
                    self.log[pidx].insert(-1, 'しおづけ')
                    # 勝敗判定
                    if self.get_winner() is not None:
                        return

        # あめまみれ
        for pidx in self.speed_order:
            p = self.pokemon[pidx]

            if p.hp and p.condition['ame_mamire']:
                self.add_rank(pidx, 5, -1)
                p.condition['ame_mamire'] -= 1
                self.log[pidx].append(f"あめまみれ 残り{p.condition['ame_mamire']}ターン")

        # 状態変化のカウント
        for pidx in self.speed_order:
            p = self.pokemon[pidx]

            if p.hp == 0:
                continue

            for s in ['encore', 'healblock', 'kanashibari', 'jigokuzuki', 'chohatsu', 'magnetrise']:
                if p.condition[s]:
                    p.condition[s] -= 1
                    self.log[pidx].append(f'{PokeDB.JPN[s]} 残り{p.condition[s]}ターン')

            # PPが切れたらアンコール解除
            if p.condition['encore'] and p.expended_moves[-1].pp == 0:
                p.condition['encore'] = 0
                self.log[pidx].append(f'アンコール解除 (PP切れ)')

        # ねむけ判定
        for pidx in self.speed_order:
            p = self.pokemon[pidx]
            if p.condition['nemuke']:
                p.condition['nemuke'] -= 1
                self.log[pidx].append(f"ねむけ 残り{p.condition['nemuke']}ターン")
                # 眠らせる
                if p.condition['nemuke'] == 0:
                    self.set_ailment(pidx, 'SLP', safeguard=False)

        # ほろびのうた判定
        for pidx in self.speed_order:
            p = self.pokemon[pidx]
            if p.hp and p.condition['horobi']:
                p.condition['horobi'] -= 1
                if p.condition['horobi'] > 0:
                    self.log[pidx].append(f"ほろびのうた 残り{p.condition['horobi']}ターン")
                else:
                    p.hp = 0
                    self.log[pidx].append('ほろびのうた 瀕死')
                    if self.get_winner() is not None:  # 勝敗判定
                        return

        # 場の効果のカウント
        for pidx in self.speed_order:
            for s in ['reflector', 'lightwall', 'safeguard', 'whitemist', 'oikaze']:
                if self.condition[s][pidx]:
                    self.condition[s][pidx] -= 1
                    self.log[pidx].append(f'{PokeDB.JPN[s]} 残り{self.condition[s][pidx]}ターン')

        for s in list(self.condition.keys())[4:10]:
            if self.condition[s]:
                self.condition[s] -= 1
                for pidx in self.speed_order:
                    self.log[pidx].append(f'{PokeDB.JPN[s]} 残り{self.condition[s]}ターン')

        # 即時アイテムの判定 (ターン終了時)
        for pidx in self.speed_order:
            if self.pokemon[pidx].item.immediate and self.pokemon[pidx].hp:
                self.activate_item(pidx)

        # はねやすめ解除
        for pidx in self.speed_order:
            if self.pokemon[pidx].executed_move == 'はねやすめ' and \
                    self.move_succeeded[pidx] and 'ひこう' in self.pokemon[pidx].lost_types:
                self.pokemon[pidx].lost_types.remove('ひこう')
                self.log[pidx].append('はねやすめ解除')

        # その他
        for pidx in self.speed_order:
            p1 = self.pokemon[pidx]
            p2 = self.pokemon[not pidx]

            if p1.hp == 0:
                continue

            if p1.ability.name in ['スロースタート', 'かそく', 'しゅうかく', 'ムラっけ', 'ナイトメア']:
                self.activate_ability(pidx)

            if p1.ability == 'はんすう' and p1.ability.count:
                self.activate_ability(pidx)

            if p1.item.name in ['かえんだま', 'どくどくだま']:
                self.activate_item(pidx)

            # 勝敗判定
            if self.get_winner() is not None:
                return

    ##################### 実機Bot #####################

    def main_loop(self):
        """実機で対戦する
        オンラインなら試合が終わるまでループし、オフラインなら無限周回する"""

        print(
            f"\n{'#'*50}\n{'対人戦' if self.mode == BattleMode.ONLINE else '学校最強大会'}\n{'#'*50}\n")

        # ログに記録
        self.game_log['mode'] = self.mode.value
        self.game_log['n_selection'] = self.n_selection
        self.game_log['seed'] = self.seed
        self.game_log["team_0"] = [p.dump() for p in self.player[0].team]
        self.game_log["selection_indexes_0"] = self.selection_indexes[0]

        if self.mode == BattleMode.OFFLINE:
            self.press_button('B', n=5)

        # ターン処理
        while True:
            if self.read_phase():
                # 操作できるフェーズ
                if self.mode == BattleMode.OFFLINE:
                    # A連打で遷移した画面から戻る
                    self.press_button('B', n=5, post_sleep=1)
                else:
                    self.none_phase_start_time = 0

            else:
                # 操作できないフェーズ
                if self.mode == BattleMode.OFFLINE:
                    self.press_button('A', post_sleep=0.3)
                else:
                    # 切断対策
                    if not self.none_phase_start_time:
                        self.none_phase_start_time = time.time()
                    elif time.time() - self.none_phase_start_time > 60:
                        print("一定時間応答がないため画面を移動します")
                        self.press_button('A', n=10)

                # ターン開始
                self.turn_start_time = time.time()

            match self.phase:
                case 'standby':
                    self.press_button('A', post_sleep=0.5)

                case 'selection':
                    if self.selection_indexes[0]:
                        continue

                    print(f"\n{'-'*20} {self.phase} {'-'*20}\n")

                    # 時間計測開始
                    t0 = time.time()

                    # 試合をリセット
                    self.game_reset()

                    # OCR履歴を削除
                    if os.path.isdir(OCR_LOG_DIR):
                        shutil.rmtree(OCR_LOG_DIR)
                        print("OCR履歴を削除しました")

                    # 相手のパーティを読み込む
                    self.press_button('B', n=5)
                    self.read_opponent_team()
                    dt = time.time() - t0

                    # コマンドを取得
                    self.selection_indexes[0] = self.player[0].selection_command(
                        self.masked(0))

                    selected_names = [
                        self.player[0].team[i].display_name for i in self.selection_indexes[0]]
                    print(f"{'='*40}\n選出 {selected_names}\n{'='*40}")

                    # コマンドを入力
                    t0 = time.time()
                    self.input_selection_command(self.selection_indexes[0])
                    dt += time.time() - t0

                    # コマンド入力にかかった時間を更新
                    print(f'操作時間 {dt:.1f}s')
                    self.selection_command_time = max(
                        self.selection_command_time, dt)

                    # 0ターン目終了
                    self.turn = 0

                case 'battle':
                    print(f"{'-'*50}\n\t{self.phase}\n{'-'*50}")

                    t0 = time.time()

                    # noneフェーズに技選択画面に移動していたら初期画面に戻る
                    if self.mode == BattleMode.OFFLINE:
                        self.press_button('B')

                    # 盤面を取得
                    if not self.read_banmen():
                        warnings.warn('Failed to read Banmen')
                        self.press_button('B', n=5)
                    else:
                        # バッファを処理
                        self.process_text_buffer()

                        # 現状 (=前ターンの終状態) をログに記録
                        self.game_log[f"Turn_{self.turn}"] = self.dump()

                        # 前ターンの処理を反映
                        for p in self.pokemon:
                            if p.expended_moves:
                                p.active_turn += 1

                                if p.item.name[:4] == 'こだわり' and not p.choice_locked:
                                    p.choice_locked = True

                            if p.ailment == 'SLP' and p.sleep_turn > 1:
                                p.sleep_turn -= 1

                        # 相手の場のポケモンを表示
                        print(f"\n相手\t{self.pokemon[1]}")

                        # コマンドを取得
                        dt = time.time() - t0
                        cmd = self.player[0].battle_command(self.masked(0))
                        t0 = time.time()

                        print(f"{'='*40}\n\t{self.cmd2str(0, cmd)}\n{'='*40}")

                        # ターン経過
                        self.turn += 1

                        # コマンドを入力
                        if self.input_battle_command(cmd):
                            # コマンド入力にかかった時間を更新
                            dt += time.time() - t0
                            print(f'操作時間 {dt:.1f}s')
                            self.battle_command_time = max(
                                self.battle_command_time, dt)

                            # コマンド
                            self.command[0] = cmd

                            # ターン処理
                            if cmd in range(10, 20):
                                # テラスタル
                                self.pokemon[0].terastal = True

                            elif cmd in CommandRange['switch']:
                                # 交代
                                self.switch_pokemon(
                                    pidx=0, command=cmd, landing=False)

                            # 連続で入力しないための待ち時間
                            time.sleep(1)

                        else:
                            warnings.warn(f'Failed to input commands')
                            self.press_button('B', n=5)
                            continue

                        # 読み取り履歴を削除
                        self.recognized_labels.clear()

                case 'switch':
                    print(f"\n{'-'*20} {self.phase} {'-'*20}\n")

                    t0 = time.time()

                    # オフライン対戦の入れ替え画面から抜ける
                    if self.mode == BattleMode.OFFLINE:
                        self.press_button('B', n=4, post_sleep=0.5)
                        if self.read_phase() != 'switch':
                            continue

                    for i in range(len(self.selection_indexes[0])):
                        # 自分のポケモンのHPを取得
                        if (hp := self.read_switch_hp(i, capture=(i == 0))) == 0:
                            # 0なら再確認
                            hp = self.read_switch_hp(i, capture=True)

                        # HPを更新
                        p = Pokemon.find(self.selected_pokemons(
                            0), display_name=self.read_switch_name(i))
                        p.hp = hp

                        print(f'\t{p.name} HP {p.hp}/{p.stats[0]}')

                        # 先頭のポケモンを場のポケモンに更新
                        if i == 0:
                            self.pokemon[0] = p

                    # バッファを処理
                    self.process_text_buffer()

                    # コマンドを取得
                    dt = time.time() - t0
                    cmd = self.player[0].switch_command(self.masked(0))
                    t0 = time.time()

                    print(f"{'='*40}\n\t{self.cmd2str(0, cmd)}\n{'='*40}")

                    # コマンドを入力
                    self.input_switch_command(cmd)

                    # コマンド入力にかかった時間を更新
                    dt += time.time() - t0
                    print(f'操作時間 {dt:.1f}s')
                    self.switch_command_time = max(
                        self.switch_command_time, dt)

                    # 交代
                    self.switch_pokemon(pidx=0, command=cmd, landing=False)

                    # 読み取り履歴を削除
                    self.recognized_labels.clear()

                    # 連続で入力しないための待ち時間
                    time.sleep(2)

                case _:
                    # 試合開始前ならスキップ
                    if not self.selection_indexes[1]:
                        continue

                    # 画面のテキストを取得
                    if self.read_screen_text(capture=False):
                        # 特性テキストも取得
                        for pidx in range(2):
                            self.read_ability_text(pidx, capture=False)

                    if self.mode == BattleMode.OFFLINE:
                        self.press_button('A', post_sleep=0.5)

                    elif (s := self.read_win_loss(capture=False)):
                        # 勝敗の観測
                        self.winner = 0 if s == 'win' else 1
                        break

                    # 読み取り履歴を削除
                    self.recognized_labels.clear()

        # ログに記録
        self.game_log["team_1"] = [p.dump() for p in self.player[1].team]
        self.game_log["selection_indexes_1"] = self.selection_indexes[1]
        self.game_log['winner'] = self.winner

    def game_time(self):
        """残りの試合時間"""
        elapsed_time = time.time() - self.start_time
        return Time.GAME.value - elapsed_time

    def thinking_time(self):
        """残りのターン持ち時間"""
        match self.phase:
            case 'selection':
                return Time.SELECTION.value - self.selection_command_time - (time.time()-self.turn_start_time)
            case 'battle' | 'switch':
                return Time.COMMAND.value - self.battle_command_time - (time.time()-self.turn_start_time)
            case _:
                return 1e10

    def overwrite_condition(self, player_idx: int, condition: dict):
        """場とポケモンの状態を上書きする"""
        p = self.pokemon[player_idx]

        # オーロラベールを両壁に書き換える
        if 'auroraveil' in condition:
            condition['reflector'] = condition['lightwall'] = condition['auroraveil']
            del condition['auroraveil']

        # 引数の条件にない項目をリセット
        for s in self.condition:
            if s not in condition:
                self.condition[s] = [0, 0] if type(
                    self.condition[s]) == list else 0

        for s in p.condition:
            if s not in condition:
                p.condition[s] = 0

        for s in condition:
            # 場の状態を更新
            if s in self.condition:
                if s in list(self.condition.keys())[:10]:
                    self.condition[s] = condition[s]
                else:
                    self.condition[s][player_idx] = condition[s]

            # ポケモンの状態を更新
            elif s in p.condition:
                if s == 'badpoison':
                    p.condition[s] += 1
                elif s == 'bind':
                    p.condition[s] = max(1, p.condition[s] - 1) + 0.8
                elif s == 'confusion':
                    p.condition[s] = max(1, p.condition[s] - 1)
                else:
                    p.condition[s] = condition[s]

    def input_selection_command(self, command: list[int]):
        """選出コマンドを入力する"""
        for cmd in command + [6]:   # [6] 決定ボタン
            while True:
                pos = self.selection_cursor_position()
                if pos == cmd:
                    break

                n = cmd - pos
                button = 'DPAD_DOWN' if n > 0 else 'DPAD_UP'
                self.press_button(button, n=abs(n), post_sleep=Time.CAPTURE.value+0.1)

                # 入力に失敗した場合、先頭のn匹が選出される
                if self.read_phase() != 'selection':
                    warnings.warn('Failed to input commands')
                    self.selection_indexes[0] = list(range(self.n_selection))
                    return

            self.press_button('A', n=2, interval=0.2)

        self.selection_indexes[0] = command

    def input_switch_command(self, command: int) -> bool:
        """交代コマンドを入力する"""
        self.press_button('DPAD_DOWN', post_sleep=Time.CAPTURE.value+0.2)

        for i in range(len(self.selection_indexes[0])-2):
            if self.read_survival() == 'alive':
                display_name = self.read_switch_name(i+1)
                if display_name == self.player[0].team[command-100].display_name:
                    break

            self.press_button('DPAD_DOWN', post_sleep=Time.CAPTURE.value+0.1)

            if self.read_phase() != 'switch':
                warnings.warn('Invalid screen')
                return False

        self.press_button('A', n=2, interval=0.2)
        return True

    def input_battle_command(self, command):
        """行動コマンドを入力する"""
        if command == Command.STRUGGLE:
            self.press_button('A', n=5)

        elif command in CommandRange['battle']:
            # 技選択画面に移動
            while True:
                if (pos := self.battle_cursor_position()) == 0:
                    break
                self.press_button('DPAD_UP', n=pos, post_sleep=Time.CAPTURE.value)

            self.press_button('A', post_sleep=1)

            # PPを取得
            for i, move in enumerate(self.pokemon[0].moves):
                v = self.read_pp(idx=i, capture=(i == 0))

                # PPが0ならダブルチェック
                if v == 0 and v != move.pp:
                    v = self.read_pp(idx=i, capture=True)

                move.pp = v

            if not self.mute:
                print(f'PP {[move.pp for move in self.pokemon[0].moves]}')

            # PPがなければ中断
            if self.pokemon[0].moves[command % 10].pp == 0:
                warnings.warn(f"PP is zero : {move}")
                return False

            # テラスタル
            if command in CommandRange['terastal']:
                self.press_button('R')

            # 技を入力
            while True:
                if (pos := self.move_cursor_position()) == command % 10:
                    break
                dpos = command % 10 - pos
                button = 'DPAD_DOWN' if dpos > 0 else 'DPAD_UP'
                self.press_button(button, n=abs(
                    dpos), post_sleep=Time.CAPTURE.value)
                if self.read_phase() != 'battle':
                    return False

            self.press_button('A')

        # 交代
        elif command in CommandRange['switch']:
            # 交代画面に移動
            while True:
                if (pos := self.battle_cursor_position()) == 1:
                    break
                dpos = 1 - pos
                button = 'DPAD_DOWN' if dpos > 0 else 'DPAD_UP'
                self.press_button(button, n=abs(dpos), post_sleep=Time.TRANSITION_CAPTURE.value)
                if self.read_phase() != 'battle':
                    return False

            self.press_button('A', post_sleep=0.5)

            # 交代入力
            if self.is_switch_window():
                self.input_switch_command(command)
            else:
                return False

        else:
            return False

        return True

    def is_selection_window(self, capture: bool = True):
        """選出画面ならTrue"""
        if capture:
            self.capture()

        img1 = ut.BGR2BIN(self.img[14:64, 856:906],
                          threshold=100, bitwise_not=True)
        return ut.template_match_score(img1, self.template_selection) > 0.99

    def is_battle_window(self, capture: bool = True):
        """ターン開始時の画面ならTrue"""
        if capture:
            self.capture()

        img1 = ut.BGR2BIN(self.img[997:1039, 827:869],
                          threshold=200, bitwise_not=True)
        # 黄色点滅時にも読み取れるように閾値を下げている
        return ut.template_match_score(img1, self.template_battle) > 0.95

    def is_switch_window(self, capture: bool = True):
        """交代画面ならTrue"""
        if capture:
            self.capture()

        img1 = ut.BGR2BIN(self.img[140:200, 770:860],
                          threshold=150, bitwise_not=True)
        return ut.template_match_score(img1, self.template_switch) > 0.99

    def is_standby_window(self, capture: bool = True):
        """オンライン対戦の待機画面ならTrue"""
        if capture:
            self.capture()

        img1 = ut.BGR2BIN(self.img[10:70, 28:88],
                          threshold=100, bitwise_not=True)
        return ut.template_match_score(img1, self.template_standby) > 0.99

    def is_condition_window(self, capture: bool = True):
        """場の状態の確認画面ならTrue"""
        if capture:
            self.capture()

        img1 = ut.BGR2BIN(self.img[76:132, 1112:1372],
                          threshold=200, bitwise_not=True)
        return ut.template_match_score(img1, self.template_condition_window) > 0.99

    def selection_cursor_position(self, capture: bool = True):
        """選出画面でのカーソル位置
            0~5     ポケモン
            6       完了ボタン
        """
        if capture:
            self.capture()

        for i in range(6):
            img1 = cv2.cvtColor(
                self.img[200+116*i:250+116*i, 500:550], cv2.COLOR_BGR2GRAY)
            # cv2.imwrite(f"{OCR_LOG_DIR}/{i}.png", img1)
            if img1[0, 0] > 150:
                return i

        return 6

    def battle_cursor_position(self, capture: bool = True):
        """行動選択画面でのカーソル位置
            オンライン -> 0: たたかう, 1:ポケモン, 2:にげる
            オフライン -> 0: たたかう, 1:ポケモン, 2:バッグ, 3:にげる
        """
        if capture:
            self.capture()

        y0 = 700 if self.mode == BattleMode.OFFLINE else 788
        for i in range(4):
            img1 = cv2.cvtColor(
                self.img[y0+88*i:y0+88*i+70, 1800:1850], cv2.COLOR_BGR2GRAY)
            if img1[0, 0] > 150:
                return i

        return 0

    def move_cursor_position(self, capture: bool = True):
        """技選択画面でのカーソル位置"""
        if capture:
            self.capture()

        for i in range(4):
            img1 = cv2.cvtColor(
                self.img[680+112*i:700+112*i, 1420:1470], cv2.COLOR_BGR2GRAY)
            # cv2.imwrite(f"{OCR_LOG_DIR}/trim_{i}.png", img1)
            if img1[0, 0] > 150:
                return i

        return 0

    def read_banmen(self):
        """盤面の情報を取得"""
        self.press_button('Y', post_sleep=Time.TRANSITION_CAPTURE.value)

        # 相手にテラスタル権があれば、テラスタイプを確認
        opponent_terastal = self.read_opponent_terastal() if self.can_terastallize(1) else None

        # 自分の盤面を取得
        if 'player0' not in self.recognized_labels:
            if not self.mute:
                print('自分の盤面')

            self.press_button('A', post_sleep=Time.TRANSITION_CAPTURE.value+0.5)

            if not self.is_condition_window():
                warnings.warn('Invalid screen')
                return False

            # 場のポケモンを取得
            display_name = self.read_display_name(pidx=0, capture=False)

            # 場のポケモンの修正
            if not self.pokemon[0] or display_name != self.pokemon[0].display_name:
                p = Pokemon.find(self.player[0].team, display_name=display_name)
                self.switch_pokemon(pidx=0, p=p, landing=False)

            # ポケモンの状態の修正
            self.pokemon[0].hp = max(1, min(self.read_hp(capture=False), self.pokemon[0].stats[0]))
            self.pokemon[0].ailment = self.read_ailment(capture=False)
            self.pokemon[0].rank[1:] = self.read_rank(capture=False)
            self.overwrite_condition(pidx=0, condition=self.read_condition(capture=False))

            # アイテムの修正
            if (item := self.read_item(capture=False)) != self.pokemon[0].item:
                if item:
                    self.pokemon[0].item = Item(item)
                    if not self.mute:
                        print(f"\tアイテム {self.pokemon[0].item}")
                else:
                    self.pokemon[0].item.active = False
                    if not self.mute:
                        print(f"\t失ったアイテム {self.pokemon[0].item.name_lost}")

                self.pokemon[0].choice_locked = False  # アイテム変化 = こだわり解除
                self.pokemon[0].item.observed = True  # 観測

            # 認識完了
            self.recognized_labels.append('player0')

        else:
            self.press_button('A', post_sleep=0.2)

        # 相手の盤面を取得
        opponent_switched = False

        if not 'player1' in self.recognized_labels:
            if not self.mute:
                print('相手の盤面')

            self.press_button('R', post_sleep=Time.TRANSITION_CAPTURE.value)

            if not self.is_condition_window():
                warnings.warn('Invalid screen')
                return False

            # 場のポケモンを取得
            display_name = self.read_display_name(pidx=1, capture=False)

            if self.mode == BattleMode.OFFLINE:
                # オフライン対戦では、対面している相手ポケモン = 相手の全選出 とみなす
                name = PokeDB.display_name2names[display_name][0]
                self.pokemon[1] = Pokemon(name)
                self.pokemon[1].level = 80
                self.pokemon[1].observed = True
                self.player[1].team = [self.pokemon[1]]
                self.selection_indexes[1] = [0]

            elif not self.pokemon[1] or display_name != self.pokemon[1].display_name:
                opponent_switched = True

                # 初見なら相手選出に追加
                if display_name not in [p.display_name for p in self.selected_pokemons(1)]:
                    idx = Pokemon.index(self.player[1].team, display_name=display_name)
                    self.switch_pokemon(pidx=1, idx=idx, landing=False)

                    # フォルムを識別
                    if (name := self.read_form(display_name, capture=False)):
                        self.pokemon[1].name = name

                    if not self.mute:
                        print(
                            f'\t選出 {[p.name for p in self.selected_pokemons(1)]}')

            # 相手のテラスタルを取得
            if opponent_terastal:
                self.pokemon[1].terastal = opponent_terastal
                self.pokemon[1].terastal = True

            self.pokemon[1].hp_ratio = self.read_hp_ratio(capture=False)
            self.pokemon[1].ailment = self.read_ailment(capture=False)
            self.pokemon[1].rank[1:] = self.read_rank(capture=False)
            self.overwrite_condition(
                pidx=1, condition=self.read_condition(capture=False))

            # 認識完了
            self.recognized_labels.append('player1')

        # コマンド選択画面に戻る
        while True:
            self.press_button(
                'B', n=5, post_sleep=Time.TRANSITION_CAPTURE.value)
            if self.is_battle_window():
                break

        # 相手が交代していれば、相手の控えが瀕死かどうか確認
        if opponent_switched:
            self.press_button('PLUS', post_sleep=Time.TRANSITION_CAPTURE.value)
            self.read_opponent_survival()
            self.press_button('B', post_sleep=0.2)

        return True

    def read_pp(self, idx, capture: bool = True):
        """技選択画面からPPを読み取る"""
        if capture:
            self.capture()

        for thr in [200, 150, 120]:
            img1 = ut.BGR2BIN(
                self.img[660+112*idx:700+112*idx, 1755:1800], threshold=thr, bitwise_not=True)
            # cv2.imwrite(f"{OCR_LOG_DIR}/trim_{idx}.png", img1)
            s = ut.OCR(img1, lang='num', log_dir=OCR_LOG_DIR / "pp")
            if s and not s[-1].isdigit():
                s = s[:-1]
            if s.isdigit():
                return int(s)

        return 0

    def read_phase(self, capture: bool = True):
        """現在の場面を読み取る"""
        if self.is_battle_window(capture=capture):
            self.phase = 'battle'
        elif self.is_switch_window(capture=False):
            self.phase = 'switch'
        elif self.is_selection_window(capture=False):
            self.phase = 'selection'
        elif self.is_standby_window(capture=False):
            self.phase = 'standby'
        else:
            self.phase = None

        return self.phase

    def read_survival(self, capture: bool = True):
        """交代画面でポケモンの状態(alive/fainting/in_battle)を読み取る"""
        if capture:
            self.capture()

        img1 = ut.BGR2BIN(self.img[140:200, 1060:1260],
                          threshold=150, bitwise_not=True)
        # cv2.imwrite(f"{OCR_LOG_DIR}/trim_{i}.png", img1)

        for s in self.template_alives:
            if ut.template_match_score(img1, self.template_alives[s]) > 0.99:
                return s

    def read_switch_name(self, idx: int, capture: bool = True):
        """交代画面で自分のポケモンの表示名を読み取る"""
        if capture:
            self.capture()

        img1 = ut.BGR2BIN(
            self.img[171+126*idx:212+126*idx, 94:300], threshold=100)
        # cv2.imwrite(f"{OCR_LOG_DIR}/trim_{idx}.png", img1)
        candidates = sum(
            [PokeDB.jpn2foreign_display_names[p.display_name]
                for p in self.selected_pokemons(0)], []
        )
        s = ut.OCR(img1, candidates=candidates, lang='all',
                   log_dir=OCR_LOG_DIR / "change_name")

        display_name = PokeDB.foreign2jpn_display_name[s]  # 和訳
        # print('\t{display_name=}')
        return display_name

    def read_switch_hp(self, idx: int, capture: bool = True):
        """交代画面で自分のポケモンの残りHPを読み取る"""
        if capture:
            self.capture()

        img1 = ut.BGR2BIN(
            self.img[232+126*idx:268+126*idx, 110:298], threshold=220, bitwise_not=True)
        # cv2.imwrite(f"{OCR_LOG_DIR}/trim.png", img1)

        s = ut.OCR(img1, lang='eng')
        s = s[:s.find('/')]
        s = s.replace('T', '7')

        hp = 0 if not s.isdigit() else int(s)
        return hp

    def read_opponent_team(self, capture: bool = True):
        """選出画面で相手のパーティを読み取る"""
        if capture:
            self.capture()

        if not self.mute:
            print('相手パーティ')

        self.player[1].team = []
        trims = []

        # アイコン
        for i in range(6):
            y0 = 236+101*i-(i < 2)*2
            trims.append(ut.box_trim(
                self.img[y0:(y0+94), 1246:(1246+94)], threshold=200))
            trims[i] = cv2.cvtColor(trims[i], cv2.COLOR_BGR2GRAY)

        candidates = list(PokeDB.home.keys())

        scores, names = [0]*6, ['']*6

        for filename in glob.glob(ut.path_str("assets", "template", "*.png")):
            s = PokeDB.template_file_code[Path(filename).stem]
            if s not in candidates:
                continue
            template = cv2.cvtColor(cv2.imread(filename), cv2.COLOR_BGR2GRAY)

            for i in range(6):
                w, h = trims[i].shape[1], trims[i].shape[0]
                if w < 2 or h < 2:
                    break
                ht = int(w*template.shape[0]/template.shape[1])
                if abs(ht-h) > 3:
                    continue
                score = ut.template_match_score(
                    trims[i], cv2.resize(template, (w, ht)))
                if scores[i] < score:
                    scores[i] = score
                    names[i] = s

        # 相手のパーティに追加
        for i, name in enumerate(names):
            # 名前の修正
            if 'イルカマン' in name:
                name = 'イルカマン(ナイーブ)'

            # ポケモンを追加
            self.player[1].team.append(Pokemon(name))

            if not self.mute:
                print(f'\t{i+1}: {name}')

        # 性別
        # for i in range(6):
        #    y0 = 250+101*i
        #    img1 = self.img[y0:(y0+94), 1400:(1500)]
        #    cv2.imwrite(f"{OCR_LOG_DIR}/trim_{i}.png", img1)
        #    img1 = cv2.cvtColor(trims[i], cv2.COLOR_BGR2GRAY)

    def read_opponent_terastal(self, capture: bool = True):
        """相手の場のポケモンのテラスタイプを読み取る"""
        if capture:
            self.capture()

        terastal = None
        img1 = ut.BGR2BIN(self.img[200:282, 810:882],
                          threshold=230, bitwise_not=True)
        img1 = img1[24:-26, 20:-22]

        # 有色 = テラスタルしている
        if cv2.minMaxLoc(img1)[0] == 0:
            max_score, terastal = 0, None
            for t in self.template_terastals:
                score = ut.template_match_score(img1, self.template_terastals[t])
                if max_score < score:
                    max_score = score
                    terastal = t

        if terastal:
            print(f'\t相手 {terastal}T')

        return terastal

    def read_display_name(self, player_idx: int = 0, capture: bool = True):
        """場のポケモンの表示名を読み取る"""
        if capture:
            self.capture()

        img1 = ut.BGR2BIN(self.img[80:130, 160:450],
                          threshold=200, bitwise_not=True)

        candidates = []
        if self.mode == BattleMode.OFFLINE and player_idx == 1:
            candidates = list(PokeDB.display_name2names.keys())
        else:
            for p in self.player[player_idx].team:
                candidates += PokeDB.jpn2foreign_display_names[p.display_name]

        s = ut.OCR(img1, lang='all', candidates=candidates,
                   log_dir=OCR_LOG_DIR / "display_name")
        display_name = PokeDB.foreign2jpn_display_name[s]  # 和訳

        if not self.mute:
            print(f'\t名前 {display_name}')

        return display_name

    def read_hp(self, capture: bool = True):
        """場のポケモンの残りHPを読み取る"""
        if capture:
            self.capture()

        img1 = ut.BGR2BIN(self.img[475:515, 210:293],
                          threshold=200, bitwise_not=False)

        s = ut.OCR(img1, lang='num', log_dir=OCR_LOG_DIR / "hp")
        if s and not s[-1].isdigit():
            s = s[:-1]

        if s.isdigit():
            hp = max(1, int(s))
            if not self.mute:
                print(f'\tHP {hp}')
        else:
            warnings.warn(f'HP must be a number : {s}')
            hp = 1

        return hp

    def read_hp_ratio(self, capture: bool = True):
        """場のポケモンのHP割合を読み取る"""
        if capture:
            self.capture()

        dy, dx = 46, 242
        img1 = ut.BGR2BIN(
            self.img[472:(472+dy), 179:(179+dx)], threshold=100, bitwise_not=True)

        count = 0
        for i in range(dx):
            if img1.data[int(dy/2), i] == 0:
                count += 1

        rhp = max(0.001, min(1, count/240))
        if not self.mute:
            print(f'\tHP {int(rhp*100):.1f}%')

        return rhp

    def read_item(self, capture: bool = True):
        """場のポケモンのアイテムを読み取る"""
        if capture:
            self.capture()

        img1 = ut.BGR2BIN(self.img[350:395, 470:760],
                          threshold=230, bitwise_not=True)
        # cv2.imwrite(f"{OCR_LOG_DIR}/trim.png", img1)

        return ut.OCR(img1, candidates=list(PokeDB.items.keys())+[''], log_dir=OCR_LOG_DIR / "item")

    def read_rank(self, capture: bool = True):
        """場のポケモンの能力ランクを読み取る"""
        if capture:
            self.capture()

        dx, dy, y1 = 40, 60, 15
        ranks = [0]*7

        for j in range(7):
            y = 595 + dy*j + y1*(j > 4)

            for i in range(6):
                x = 500 + dx*i
                if self.img[y-2, x][1] > 190:  # 緑
                    ranks[j] += 1
                elif self.img[y+2, x][1] < 80:  # 赤
                    ranks[j] -= 1
                else:
                    break

        if any(ranks) and not self.mute:
            print('\t能力ランク ' + ' '.join([s + ('+' if v > 0 else '') +
                                         str(v) for s, v in zip(PokeDB.stats_label[1:], ranks) if v]))

        return ranks

    def read_ailment(self, capture: bool = True):
        """場のポケモンの状態異常を読み取る"""
        if capture:
            self.capture()

        # cv2.imwrite(f"{OCR_LOG_DIR}/trim.png",self.img[430:460, 270:360])
        img1 = ut.BGR2BIN(self.img[430:460, 270:360],
                          threshold=200, bitwise_not=True)

        for ailment in self.template_ailments:
            if ut.template_match_score(img1, self.template_ailments[ailment]) > 0.99:
                if not self.mute:
                    print(f'\t状態異常 {ailment}')
                return ailment

    def read_condition(self, capture: bool = True):
        """場とポケモンの状態変化を読み取る"""
        if capture:
            self.capture()

        dy = 86
        condition = {}

        for i in range(6):
            img1 = ut.BGR2BIN(
                self.img[188+dy*i:232+dy*i, 1190:1450], threshold=128)
            if cv2.minMaxLoc(img1)[0]:
                break

            if cv2.countNonZero(img1)/img1.size < 0.5:
                img1 = cv2.bitwise_not(img1)

            for t in self.template_conditions:
                if ut.template_match_score(img1, self.template_conditions[t]) > 0.99:
                    if t in self.limited_conditions:
                        # 残りターン数を取得
                        img2 = ut.BGR2BIN(
                            self.img[188+dy*i:232+dy*i, 1710:1733], threshold=128)

                        # ハイライトなら色を反転
                        if cv2.countNonZero(img2)/img2.size < 0.5:
                            img2 = cv2.bitwise_not(img2)

                        for j in range(len(self.template_condition_turns)):
                            if ut.template_match_score(img2, self.template_condition_turns[j]) > 0.99:
                                condition[t] = j+1
                                break

                        # ねがいごと回復設定 (要実装)
                        if t == 'wish':
                            pass

                    elif t in self.countable_conditions:
                        # カウントを取得
                        img2 = ut.BGR2BIN(
                            self.img[188+dy*i:232+dy*i, 1738:1766], threshold=128)
                        if cv2.countNonZero(img2)/img2.size < 0.5:
                            img2 = cv2.bitwise_not(img2)

                        for j in range(len(self.template_condition_counts)):
                            if ut.template_match_score(img2, self.template_condition_counts[j]) > 0.99:
                                condition[t] = j+1
                                break

                    elif t == 'horobi':
                        # 滅びカウントを取得
                        img2 = ut.BGR2BIN(
                            self.img[188+dy*i:232+dy*i, 1725:1755], threshold=128)
                        if cv2.countNonZero(img2)/img2.size < 0.5:
                            img2 = cv2.bitwise_not(img2)

                        for j in range(len(self.template_condition_horobis)):
                            if ut.template_match_score(img2, self.template_condition_horobis[j]) > 0.99:
                                condition[t] = j+1
                                break
                    else:
                        condition[t] = 1

                    break

        if condition and not self.mute:
            print(f'\t{condition}')

        return condition

    def read_opponent_survival(self, capture: bool = True):
        """パーティ確認画面で相手のポケモンが瀕死かどうか確認する"""
        if capture:
            self.capture()

        dy = 102

        for i, p in enumerate(self.player[1].team):
            img1 = ut.BGR2BIN(
                self.img[280+dy*i:302+dy*i, 1314:1334], threshold=128)

            if ut.template_match_score(img1, self.template_fainting_symbol) > 0.99:
                # 出オチした相手ポケモンを選出に追加する
                self.selection_indexes[1].append(i)
                p.hp = 0
                p.observed = True  # 観測

                if not self.mute:
                    print(f'瀕死 {p.display_name}')

    def read_team_from_box(self):
        """ボックス画面からパーティを読み込む"""
        team = []

        # 画面判定用のテンプレート画像の読み込み
        template = ut.BGR2BIN(cv2.imread(ut.path_str(
            "assets", "screen", "judge.png")), threshold=128)

        if not self.mute:
            print(f"ボックス画面からポケモンを読み取り中...\n{'-'*50}")

        # ボックスのポケモンを取得
        for i in range(6):
            self.capture()
            img1 = ut.BGR2BIN(self.img[1020:1060, 1372:1482], threshold=128)

            if ut.template_match_score(img1, template) < 0.95:
                warnings.warn('Invalid screen')
                if i == 0:
                    return
                else:
                    break

            team.append(self.read_pokemon_from_box())
            self.press_button('DPAD_DOWN', post_sleep=Time.CAPTURE.value+0.2)

        # カーソルをもとの位置に戻す
        self.press_button('DPAD_UP', n=len(team))

        return team

    def read_pokemon_from_box(self):
        """ボックスのidx番目のポケモンを読み込む"""
        self.capture()

        # 特性：フォルムの識別に使うため先に読み込む
        img1 = ut.BGR2BIN(self.img[580:620, 1455:1785], threshold=180, bitwise_not=True)
        ability_name = ut.OCR(img1, candidates=PokeDB.abilities, log_dir=OCR_LOG_DIR / "box_ability")

        # 名前
        img1 = ut.BGR2BIN(self.img[90:130, 1420:1620], threshold=180, bitwise_not=True)
        display_name = ut.OCR(img1, candidates=list(
            PokeDB.display_name2names.keys()), log_dir=OCR_LOG_DIR / "box_name")
        name = PokeDB.display_name2names[display_name][0]

        # フォルム識別
        if display_name in PokeDB.form_diff:
            for s in PokeDB.display_name2names[display_name]:
                # タイプで識別
                if PokeDB.form_diff[display_name] == 'type':
                    types = []
                    for t in range(2):
                        img1 = ut.BGR2BIN(
                            self.img[150:190, 1335+200*t:1480+200*t], threshold=230)
                        type = ut.OCR(img1, candidates=PokeDB.types,
                                      log_dir=OCR_LOG_DIR / "box_type")
                        types.append(type)
                    if types == PokeDB.zukan[s]['type'] or [types[1], types[0]] == PokeDB.zukan[s]['type']:
                        name = s
                        break
                # 特性で識別
                elif PokeDB.form_diff[display_name] == 'ability' and ability_name in PokeDB.zukan[s]['ability']:
                    name = s
                    break

        # ポケモンの生成
        p = Pokemon(name)
        p.ability.org_name = ability_name

        # 特性の修正
        if p.ability.name not in PokeDB.zukan[name]['ability']:
            p.ability.org_name = PokeDB.home[name]['ability'][0] if \
                name in PokeDB.home else PokeDB.zukan[name]['ability'][0]

        # 性格
        x = [1590, 1689, 1689, 1491, 1491, 1590]
        y = [267, 321, 437, 321, 437, 491]
        nature_correction = [1]*6
        for j in range(6):
            if self.img[y[j], x[j]][2] < 50:
                nature_correction[j] = 0.9
            elif self.img[y[j], x[j]][1] < 80:
                nature_correction[j] = 1.1
        for nature in PokeDB.nature_corrections:
            if nature_correction == PokeDB.nature_corrections[nature]:
                p.nature = nature
                break

        # もちもの
        img1 = ut.BGR2BIN(self.img[635:685, 1455:1785],
                          threshold=180, bitwise_not=True)
        p.item = Item(ut.OCR(img1, candidates=list(PokeDB.items.keys()) + [''],
                             log_dir=OCR_LOG_DIR / "box_item"))

        # テラスタイプ
        x0 = 1535+200*(len(p.types)-1)
        img1 = ut.BGR2BIN(self.img[154:186, x0:x0+145],
                          threshold=240, bitwise_not=True)
        p.terastal = ut.OCR(img1, candidates=PokeDB.types, log_dir=OCR_LOG_DIR / "box_terastal")

        # 技
        p.moves.clear()
        for j in range(4):
            img1 = ut.BGR2BIN(
                self.img[700+60*j:750+60*j, 1320:1570], threshold=180, bitwise_not=True)
            move = ut.OCR(img1, candidates=list(PokeDB.moves.keys()) +
                          [''], log_dir=OCR_LOG_DIR / "box_move")
            p.moves.append(Move(move))

        # レベル
        img1 = ut.BGR2BIN(self.img[25:55, 1775:1830],
                          threshold=180, bitwise_not=True)
        p.level = int(ut.OCR(
            img1, log_dir=OCR_LOG_DIR / "box_level/", lang='num').replace('.', ''))

        # 性別
        if self.img[40, 1855][0] > 180:
            p.gender = Gender.MALE
        elif self.img[40, 1855][1] < 100:
            p.gender = Gender.FEMALE
        else:
            p.gender = Gender.NONE

        # ステータス
        x = [1585, 1710, 1710, 1320, 1320, 1585]
        y = [215, 330, 440, 330, 440, 512]
        stats = [0]*6

        for j in range(6):
            img1 = ut.BGR2BIN(
                self.img[y[j]:y[j]+45, x[j]:x[j]+155], threshold=180, bitwise_not=True)
            s = ut.OCR(img1, lang=('eng' if j == 0 else 'num'))
            if j == 0:
                s = s[s.find('/')+1:]
            stats[j] = int(s)

        p.stats = stats

        # ザシアン・ザマゼンタの識別
        if (p.name == 'ザシアン(れきせん)' and p.item == 'くちたけん') or \
                (p.name == 'ザマゼンタ(れきせん)' and p.item == 'くちたたて'):
            p.change_form(p.name[:-5] + p.item.name[-2:] + 'のおう)')

        if not self.mute:
            print(p, end='\n\n')

        return p

    def read_form(self, display_name: str, capture: bool = True):
        """場のポケモンのフォルムを読み取る"""
        if display_name not in ['ウーラオス', 'ケンタロス', 'ザシアン', 'ザマゼンタ']:
            return ''

        if capture:
            self.capture()

        type = ['']*2
        dx = 210

        for i in range(2):
            img1 = ut.BGR2BIN(
                self.img[170:210, 525+dx*i:665+dx*i], threshold=230, bitwise_not=True)

            if cv2.minMaxLoc(img1)[0] == 255:
                type[i] = ''
            else:
                type[i] = ut.OCR(img1, candidates=PokeDB.types,
                                 log_dir=OCR_LOG_DIR / "display_type")

        for name in PokeDB.display_name2names[display_name]:
            zukan_type = PokeDB.zukan[name]['type'].copy()

            if len(zukan_type) == 1:
                zukan_type.append('')
            if zukan_type == type or zukan_type == [type[1], type[0]]:
                return name

        warnings.warn(f'\tFailed to get a form of {display_name}')
        return ''

    def read_win_loss(self, capture: bool = True):
        """勝敗を読み取る"""
        if capture:
            self.capture()

        img1 = ut.BGR2BIN(self.img[940:1060, 400:750],
                          threshold=140, bitwise_not=True)

        for s, template in self.template_winloss.items():
            if ut.template_match_score(img1, template) > 0.99:
                print(f'ゲーム終了 {s}')
                return s

    def read_screen_text(self, capture: bool = True):
        """画面下の表示テキストを読み取る"""
        if capture:
            self.capture()

        words = []

        # 文字領域にハッチがかかっていなければ中断
        img1 = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        if img1[790, 1300] > 190:
            return False

        # 行ごとにOCR
        dy = 63
        for i in range(2):
            img1 = self.img[798+dy*i:842+dy*i, 285:1400]
            img1 = ut.BGR2BIN(img1, threshold=250, bitwise_not=True)
            # cv2.imwrite(f"{OCR_LOG_DIR}/trim_{i}.png", img1)

            lang = 'all' if i == 0 else 'jpn'

            # 枠内に白文字が含まれていなければ
            # 「急所」の黄文字を狙って再OCR
            if (re_ocr := i == 0 and 0 not in img1):
                img1 = self.img[798+dy*i:842+dy*i, 285:1000]
                img1 = ut.BGR2BIN(img1, threshold=190, bitwise_not=True)
                # cv2.imwrite(f"{OCR_LOG_DIR}/trim_{i}.png", img1)
                lang = 'jpn'

            # 二値化後に黒いピクセルがなければ中断
            if 0 not in img1:
                return False

            s = ut.OCR(img1, lang=lang,
                       log_dir=OCR_LOG_DIR / "bottom_text")

            # 文字が少なければ中断
            if len(s) < 3:
                return False

            # 日本語の割合が少なければ中断
            if ut.jpn_char_ratio(s) < 0.2:
                return False

            words += ut.to_upper_jpn(s).split()

            # 黄文字は1行で構成されている
            if re_ocr:
                break

        print(f"{words=}")

        # 形式が不適切なら中断
        if len(words) < 2:
            return False

        # 濁点・半濁点なし
        worts = list(map(ut.remove_dakuten, words))

        # 学校最強大会の試合開始判定
        if self.mode == BattleMode.OFFLINE:
            if 'しかけて' in worts[-1]:
                print('*'*50, '\nNew Game\n', '*'*50)
                self.game_reset()
                self.text_buffer.clear()
                return False

        # 急所
        if any(s in worts[0] for s in ['急', '所']):
            if self.text_buffer and 'move' in self.text_buffer[-1]:
                self.text_buffer[-1]['critical'] = True
                return True
            else:
                return False

        # プレイヤーを取得
        if any(s in worts[0] for s in ['相', '手']):
            pidx = 1
            words.pop(0)
            worts.pop(0)
        else:
            pidx = 0

        # 形式が不適切なら中断
        if len(words) < 2:
            return False
        elif len(words[0]) < 3 or len(words[1]) < 3:
            return False

        dict = {'player_idx': pidx, 'display_name': words[0][:-1]}

        # 技外し
        if '当' in worts[1]:
            if self.text_buffer and 'move' in self.text_buffer[-1]:
                self.text_buffer[-1]['hit'] = False
                return True
            else:
                return False

        # ひるみ
        if 'たせな' in worts[-1]:
            dict['flinch'] = True

        # しゅうかく
        elif any(s in worts[0] for s in ['収', '穫']):
            dict['item'] = ut.find_most_similar(
                list(PokeDB.items.keys()), words[1][:-1])

        # へんげんじざい
        elif 'タイフになつ' in ''.join(worts[-2:]):
            dict['type'] = ut.find_most_similar(PokeDB.types, words[1][:-4])

        # マジシャン
        elif '奪' in worts[-1]:
            dict['item'] = ut.find_most_similar(
                list(PokeDB.items.keys()), words[1][:-1])

        # ダメージアイテム
        elif any(s in worts[1] for s in ['コツメ', 'ヤホの', 'レンフの']):
            dict['player_idx'] = int(not pidx)
            dict['display_name'] = ''
            dict['item'] = ut.find_most_similar(
                list(PokeDB.items.keys()), words[1][:-1])

        # いのちのたま
        elif '少' in worts[-1]:
            dict['item'] = 'いのちのたま'

        # ノーマルジュエル
        elif 'ノーマル' in worts[0] and '強' in words[-1]:
            dict['lost_item'] = 'ノーマルジュエル'

        # ふうせん破壊
        elif 'ふうせんか' in worts[1]:
            dict['lost_item'] = 'ふうせん'

        # ブーストエナジー
        elif '高' in worts[-1]:
            labels = PokeDB.stats_hiragana + PokeDB.stats_kanji
            s = ut.find_most_similar(labels, words[1][:-1])
            dict['boost'] = labels.index(s) % 5 + 1

        # トリック
        elif '手' in worts[-1]:
            dict['item'] = ut.find_most_similar(
                list(PokeDB.items.keys()), words[1][:-1])

        # 投げつける
        elif '投' in worts[-1]:
            dict['lost_item'] = ut.find_most_similar(
                list(PokeDB.items.keys()), words[1][:-1])

        # はたきおとす(自分が使用した場合のみ)
        elif 'をはたき' in ''.join(worts[-2:]):
            dict['player_idx'] = int(not pidx)

            s = words[1][:-1]
            if pidx == 0:
                if 'の' in s:
                    s = s[s.index('の')+1:]
                else:
                    return False

            # 対象のポケモンの表示名を照合
            selected = self.selected_pokemons(pidx)
            dict['display_name'] = Pokemon.find_most_similar(
                selected, display_name=s).display_name
            dict['lost_item'] = ut.find_most_similar(
                list(PokeDB.items.keys()), words[2][:-1])

        # みがわり発生・解除
        elif any(s in words[1] for s in ['身', '代']):
            if '現' in worts[-1]:
                dict['subst'] = True
            elif '消' in worts[-1]:
                dict['subst'] = True
            else:
                return False

        # 除外するテキスト
        # 2ブロック目に漢字
        elif any("CJK UNIFIED" in unicodedata.name(s) for s in words[1]):
            return False

        # 状態異常
        elif any(s in worts[1] for s in ['まひ', 'やけと']) or any(s in words[-1] for s in ['眠']):
            return False

        # 状態変化
        elif worts[-1][:2] == 'なつ':
            return False

        # 瀕死
        elif 'たおれ' in worts[-1]:
            return False

        # タイプ相性
        elif any(s in ''.join(words[-2:]) for s in ['効', '果']):
            return False

        # 定数ダメージ
        elif 'タメーシ' in ''.join(worts[-2:]) or any(s in words[-1] for s in ['体', '奪']):
            return False

        # 設置技
        elif any(s in words[0] for s in ['味', '方']):
            return False

        # 交代
        elif any(s in worts[-1] for s in ['戻', '引', 'くり']):
            return False

        # 変身
        elif any(s in words[-1] for s in ['変', '身']):
            return False

        # すべての技・アイテム
        else:
            # 形式が不適切なら中断
            if worts[0][-1] not in ['の', 'は']:
                return False

            # ノイズも含めてテキスト候補を用意
            candidates = list(PokeDB.moves.keys()) + PokeDB.abilities
            if worts[0][-1] == 'は':
                candidates += list(PokeDB.items.keys())

            s = ut.find_most_similar(candidates, words[1][:-1])

            # 技を読み取った場合
            if s in PokeDB.moves:
                dict['move'] = s
                dict['hit'] = True
                dict['critical'] = False
                dict['speed'] = self.pokemon[pidx].stats[5]
                dict['eff_speed'] = self.get_speed(pidx)
                dict['move_speed'] = self.get_move_speed(pidx, s, random=False)

            # アイテムを読み取った場合
            elif s in PokeDB.items:
                if s in PokeDB.consumable_items:
                    dict['lost_item'] = s
                else:
                    dict['item'] = s

        if len(dict) <= 2 or dict in self.text_buffer:
            return False

        self.text_buffer.append(dict)
        return True

    def read_ability_text(self, player_idx: int, capture: bool = True):
        """画面左右の特性テキストを読み取る"""
        if capture:
            self.capture()

        dx, dy = 1050, 44
        words = []

        # 行ごとにOCR
        for i in range(2):
            img1 = self.img[498+dy*i:540+dy*i, 300+dx*player_idx:600+dx*player_idx]
            img1 = ut.BGR2BIN(img1, threshold=250, bitwise_not=True)
            # cv2.imwrite(f"{OCR_LOG_DIR}/trim_{player_idx}_{i}.png", img1)

            lang = 'all' if i == 0 else 'jpn'

            # 「急所」の黄色テキストを読み取るために閾値を下げて再OCR
            if i == 0 and 0 not in img1:
                img1 = self.img[798+dy*i:842+dy*i, 285:1000]
                img1 = ut.BGR2BIN(img1, threshold=190, bitwise_not=True)
                # cv2.imwrite(f"{OCR_LOG_DIR}/trim_{i}.png", img1)

                # テキストがなければ中断
                if 0 not in img1:
                    return False

                lang = 'jpn'

            s = ut.OCR(img1, lang=lang,
                       log_dir=OCR_LOG_DIR / "bottom_text")
            words += s.split()

            # 形式が不適切なら中断
            if not words or words[0][-1] != 'の':
                return False

        # 形式が不適切なら中断
        if len(words) != 2:
            return False

        dict = {
            'player_idx': player_idx,
            'display_name': words[0][:-1],
            'ability': ut.find_most_similar(PokeDB.abilities, words[1])
        }

        if dict not in self.text_buffer:
            self.text_buffer.append(dict)
            # print(words)
            return True
        else:
            return False

    def process_text_buffer(self):
        """テキストバッファの情報を反映させる"""
        new_buffer = []
        move_order = []

        for i, dict in enumerate(self.text_buffer):
            pidx = dict['player_idx']

            p = Pokemon.find_most_similar(self.selected_pokemons(pidx),
                                          display_name=dict['display_name'])

            if not p:
                warnings.warn('Not found\n', dict)
                new_buffer.append(dict)  # 情報を保持
                continue

            if 'ability' in dict:
                p.ability.name = dict['ability']
                if p.ability == 'ばけのかわ':
                    p.ability.active = False
                p.ability.observed = True  # 観測

            elif 'item' in dict:
                if p.item != dict['item']:
                    p.item = Item(dict['item'])
                p.choice_locked = False
                p.item.observed = True  # 観測

            elif 'lost_item' in dict:
                if p.item != dict['item']:
                    p.item = Item(dict['item'])
                p.item.active = False
                if p.item.name_lost == 'ブーストエナジー' and p.name == self.pokemon[pidx].name:
                    p.boosted = True
                p.choice_locked = False
                p.item.observed = True  # 観測

            elif 'subst' in dict:
                if dict['subst']:
                    pass
                else:
                    p.sub_hp = 0

            elif 'type' in dict:
                p.lost_types, p.added_types = p.types, [dict['type']]

            elif 'boost' in dict:
                p.boosted_idx = dict['boost']

            elif 'move' in dict:
                # ねごとなど、1ターンに2度技の演出がある場合
                if i > 1 and 'move' in self.text_buffer[i-1] and \
                        self.text_buffer[i-1]['player_idx'] == pidx and \
                        self.text_buffer[i-1]['move'] in PokeDB.move_category['call_move']:

                    p.executed_move = p.find_move(dict['move'])

                    if pidx == 1 and p.expended_moves and p.expended_moves[-1] == 'ねごと':
                        p.add_move(p.executed_move)
                        p.moves[-1].observed = True  # 観測

                # その他の技
                else:
                    # 相手の技を追加
                    if pidx == 1 and not p.knows(dict['move']):
                        p.add_move(dict['move'])
                        p.moves[-1].observed = True  # 観測

                    move = p.find_move(dict['move'])
                    p.expended_moves.append(move)
                    p.executed_move = move

                    # PPを減らす
                    if move:
                        # プレッシャーのポケモンが場にいれば、PPが2減ったとする
                        move.add_pp(-2 if self.pokemon[not pidx].ability == 'プレッシャー' else -1)

                        # 相手の行動をコマンドに変換
                        if pidx == 1:
                            self.command[1] = self.get_command(pidx, p=p, move=move)

                    # 発動した技を記録
                    if not move_order or move_order[-1]['player_idx'] != pidx:
                        move_order.append(dict)

                self.move_succeeded[pidx] = dict['hit']

                # 技の効果を反映させる
                if self.move_succeeded[pidx]:
                    match p.executed_move:
                        case 'でんこうそうげき':
                            p.lost_types.append('でんき')
                        case 'もえつきる':
                            p.lost_types.append('ほのお')
                        case 'みがわり':
                            p.sub_hp = int(p.stats[0]/4)
                        case 'しっぽきり':
                            selected = self.selected_pokemons(pidx)
                            if (p1 := Pokemon.find(selected, name=self.pokemon[pidx].name)):
                                p1.sub_hp = int(p.stats[0]/4)
                        case 'バトンタッチ':
                            selected = self.selected_pokemons(pidx)
                            if p.sub_hp and (p1 := Pokemon.find(selected, name=self.pokemon[pidx].name)):
                                p1.sub_hp = p.sub_hp

        # 処理できなかった情報を持ち越す
        # 試合開始の認識精度が悪いため、オフライン対戦では破棄する
        self.text_buffer = new_buffer if self.mode == BattleMode.ONLINE else []

        # 両プレイヤーが使用した技の優先度が同じなら、行動順から素早さを推定する
        if len(move_order) == 2 and move_order[0]['move_speed'] == move_order[1]['move_speed']:

            # 相手の行動順index
            oidx = [dict['player_idx'] for dict in move_order].index(1)

            p = Pokemon.find(self.selected_pokemons(
                1), display_name=move_order[oidx]['display_name'])

            if p is None:
                warnings.warn(f"{move_order[oidx]['display_name']} is not in \
                              {[p.display_name for p in self.selected_pokemons(1)]}")
            else:
                # 相手のS補正値
                r_speed = move_order[oidx]['eff_speed'] / \
                    move_order[oidx]['speed']

                # 相手のS = 自分のS / 相手のS補正値
                speed = int(move_order[not oidx]['eff_speed'] / r_speed)

                # S推定値を更新
                p.set_speed_limit(speed, first_act=(oidx == 0))

    def capture(self, filename: str = None):
        """画面をキャプチャする"""
        CAP.read()
        _, self.img = CAP.read()  # バッファの都合で2回撮影する
        if filename:
            cv2.imwrite(filename, self.img)

    def press_button(self, button, n=1, interval=0.1, post_sleep=0.1):
        """ボタンを押す"""
        # コマンドのマクロを作成
        macro = ''
        for i in range(n):
            macro += f'{button} 0.1s\n'
            if i < n-1 and interval:
                macro += f'{interval}s\n'
        if post_sleep:
            macro += f'{post_sleep}s\n'

        # コマンド送信
        if macro:
            macro_id = NX.macro(NXID, macro, block=False)
            while macro_id not in NX.state[NXID]['finished_macros']:
                time.sleep(0.01)
