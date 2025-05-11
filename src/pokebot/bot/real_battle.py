import os
import sys
import time
import unicodedata
import shutil
from pathlib import Path
from importlib import resources
import warnings

import cv2
import nxbt

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Ailment, Mode, Time
import pokebot.common.utils as ut
from pokebot.core import PokeDB
from pokebot.core import Pokemon
from pokebot.core.ability import Ability
from pokebot.core.item import Item
from pokebot.core import Move
from pokebot.battle.battle import Battle


# TODO sys.path.appendで実装
os.environ["PATH"] += os.pathsep + str(resources.files("pokebot.Tesseract-OCR"))
os.environ["TESSDATA_PREFIX"] = str(resources.files("pokebot.Tesseract-OCR").joinpath("tessdata"))


OCR_LOG_DIR: Path = Path(sys.argv[0]).resolve().parent / 'ocr_log'
CAP = None
NX, NXID = None, None


class RealBattle(Battle):
    def __init__(self,
                 player1,
                 player2,
                 mode: Mode = Mode.OFFLINE,
                 n_selection: int = 3,
                 open_sheet: bool = False,
                 seed: int | None = None,
                 video_id: int = 0):

        super().__init__(player1, player2, mode, n_selection, open_sheet, seed)

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
        for s in Ailment:
            self.template_ailments[s] = (ut.BGR2BIN(cv2.imread(
                ut.path_str("assets", "screen", f"{s}.png")), threshold=200, bitwise_not=True))

        self.counts = ['auroraveil'] + list(self.count.keys()) + list(Pokemon().count.keys())

        self.limited_conditions = ['aurora_veil'] + [
            'ame_mamire', 'encore', 'healblock', 'kanashibari', 'jigokuzuki', 'chohatsu', 'magnetrise', 'nemuke',
            'sunny', 'rainy', 'snow', 'sandstorm', Field.ELEC, Field.GRASS, Field.PSYCO, Field.MIST,
            'gravity', 'trickroom', 'oikaze', 'lightwall', 'reflector', 'safeguard', 'whitemist',
        ]

        self.countable_conditions = ['stock', 'makibishi', 'dokubishi']

        self.template_conditions = {}
        for s in self.counts:
            img = ut.BGR2BIN(cv2.imread(
                ut.path_str("assets", "condition", f"{s}.png")), threshold=128)
            if cv2.countNonZero(img)/img.size < 0.5:
                img = cv2.bitwise_not(img)
            self.template_conditions[s] = img

    def init_game(self):
        super().init_game()

        self.start_time = time.time()                   # 試合開始時刻
        self.text_buffer = []                           # 読み取った画面テキストを格納
        self.recognized_labels = []                     # 認識した情報のラベルを格納
        self.none_phase_start_time = 0                  # コマンド入力できないフェーズの開始時刻

    def main_loop(self):
        """実機で対戦する
        オンラインなら試合が終わるまでループし、オフラインなら無限周回する"""

        print(
            f"\n{'#'*50}\n{'対人戦' if self.mode == Mode.ONLINE else '学校最強大会'}\n{'#'*50}\n")

        if self.mode == Mode.OFFLINE:
            self.press_button('B', n=5)

        # ターン処理
        while True:
            if self.read_phase():
                # 操作できるフェーズ
                if self.mode == Mode.OFFLINE:
                    # A連打で遷移した画面から戻る
                    self.press_button('B', n=5, post_sleep=1)
                else:
                    self.none_phase_start_time = 0

            else:
                # 操作できないフェーズ
                if self.mode == Mode.OFFLINE:
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
                    self.init_game()

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
                        self.player[0].team[i].label for i in self.selection_indexes[0]]
                    print(f"{'='*40}\n選出 {selected_names}\n{'='*40}")

                    # コマンドを入力
                    t0 = time.time()
                    self.input_selection_command(self.selection_indexes[0])
                    dt += time.time() - t0

                    # コマンド入力にかかった時間を更新
                    print(f"操作時間 {dt:.1f}s")
                    self.selection_command_time = max(
                        self.selection_command_time, dt)

                    # 0ターン目終了
                    self.turn = 0

                case 'battle':
                    print(f"{'-'*50}\n\t{self.phase}\n{'-'*50}")

                    t0 = time.time()

                    # noneフェーズに技選択画面に移動していたら初期画面に戻る
                    if self.mode == Mode.OFFLINE:
                        self.press_button('B')

                    # 盤面を取得
                    if not self.read_banmen():
                        warnings.warn('Failed to read Banmen')
                        self.press_button('B', n=5)
                    else:
                        # バッファを処理
                        self.process_text_buffer()

                        # TODO 現状 (=前ターンの終状態) をログに記録

                        # 前ターンの処理を反映
                        for p in self.pokemon:
                            if p.expended_moves:
                                p.active_turn += 1

                                if p.item.name[:4] == 'こだわり' and not p.choice_locked:
                                    p.choice_locked = True

                            if p.ailment == Ailment.SLP and p.sleep_turn > 1:
                                p.sleep_turn -= 1

                        # 相手の場のポケモンを表示
                        print(f"\n相手\t{self.pokemon[1]}")

                        # コマンドを取得
                        dt = time.time() - t0
                        cmd = self.player[0].battle_command(self.masked(0))
                        t0 = time.time()

                        print(f"{'='*40}\n\t{self.command_to_str(0, cmd)}\n{'='*40}")

                        # ターン経過
                        self.turn += 1

                        # コマンドを入力
                        if self.input_battle_command(cmd):
                            # コマンド入力にかかった時間を更新
                            dt += time.time() - t0
                            print(f"操作時間 {dt:.1f}s")
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
                            warnings.warn(f"Failed to input commands")
                            self.press_button('B', n=5)
                            continue

                        # 読み取り履歴を削除
                        self.recognized_labels.clear()

                case 'switch':
                    print(f"\n{'-'*20} {self.phase} {'-'*20}\n")

                    t0 = time.time()

                    # オフライン対戦の入れ替え画面から抜ける
                    if self.mode == Mode.OFFLINE:
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

                        print(f"\t{p.name} HP {p.hp}/{p.stats[0]}")

                        # 先頭のポケモンを場のポケモンに更新
                        if i == 0:
                            self.pokemon[0] = p

                    # バッファを処理
                    self.process_text_buffer()

                    # コマンドを取得
                    dt = time.time() - t0
                    cmd = self.player[0].switch_command(self.masked(0))
                    t0 = time.time()

                    print(f"{'='*40}\n\t{self.command_to_str(0, cmd)}\n{'='*40}")

                    # コマンドを入力
                    self.input_switch_command(cmd)

                    # コマンド入力にかかった時間を更新
                    dt += time.time() - t0
                    print(f"操作時間 {dt:.1f}s")
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

                    if self.mode == Mode.OFFLINE:
                        self.press_button('A', post_sleep=0.5)

                    elif (s := self.read_win_loss(capture=False)):
                        # 勝敗の観測
                        self._winner = PlayerIndex(0 if s == 'win' else 1)
                        break

                    # 読み取り履歴を削除
                    self.recognized_labels.clear()

        # TODO ログに記録
        self.logger.winner = self.winner()

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
        for s in self.count:
            if s not in condition:
                self.count[s] = [0, 0] if type(
                    self.count[s]) == list else 0

        for s in p.count:
            if s not in condition:
                p.count[s] = 0

        for s in condition:
            # 場の状態を更新
            if s in self.count:
                if s in list(self.count.keys())[:10]:
                    self.count[s] = condition[s]
                else:
                    self.count[s][player_idx] = condition[s]

            # ポケモンの状態を更新
            elif s in p.count:
                if s == 'badpoison':
                    p.count[s] += 1
                elif s == 'bind':
                    p.count[s] = max(1, p.count[s] - 1) + 0.8
                elif s == 'confusion':
                    p.count[s] = max(1, p.count[s] - 1)
                else:
                    p.count[s] = condition[s]

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
                if display_name == self.player[0].team[command-100].label:
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
                print(f"PP {[move.pp for move in self.pokemon[0].moves]}")

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

        y0 = 700 if self.mode == Mode.OFFLINE else 788
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
            display_name = self.read_label(pidx=0, capture=False)

            # 場のポケモンの修正
            if not self.pokemon[0] or display_name != self.pokemon[0].label:
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
            display_name = self.read_label(pidx=1, capture=False)

            if self.mode == Mode.OFFLINE:
                # オフライン対戦では、対面している相手ポケモン = 相手の全選出 とみなす
                name = PokeDB.label2names[display_name][0]
                self.pokemon[1] = Pokemon(name)
                self.pokemon[1].level = 80
                self.pokemon[1].observed = True
                self.player[1].team = [self.pokemon[1]]
                self.selection_indexes[1] = [0]

            elif not self.pokemon[1] or display_name != self.pokemon[1].label:
                opponent_switched = True

                # 初見なら相手選出に追加
                if display_name not in [p.label for p in self.selected_pokemons(1)]:
                    idx = Pokemon.index(self.player[1].team, display_name=display_name)
                    self.switch_pokemon(pidx=1, idx=idx, landing=False)

                    # フォルムを識別
                    if (name := self.read_form(display_name, capture=False)):
                        self.pokemon[1].name = name

                    if not self.mute:
                        print(f"\t選出 {[p.name for p in self.selected_pokemons(1)]}")

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
        labels = [PokeDB.jpn_to_foreign_labels[p.label] for p in self.selected_pokemons(0)]
        candidates = sum(labels, [])
        s = ut.OCR(img1, candidates=candidates, lang='all', log_dir=OCR_LOG_DIR / "change_name")

        display_name = PokeDB.foreign_to_jpn_label[s]  # 和訳
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

        for filename in ut.path("assets", "template").glob("*.png"):
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
                print(f"\t{i+1}: {name}")

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
            print(f"\t相手 {terastal}T")

        return terastal

    def read_label(self, player_idx: int = 0, capture: bool = True):
        """場のポケモンの表示名を読み取る"""
        if capture:
            self.capture()

        img1 = ut.BGR2BIN(self.img[80:130, 160:450], threshold=200, bitwise_not=True)

        candidates = []
        if self.mode == Mode.OFFLINE and player_idx == 1:
            candidates = list(PokeDB.label_to_names.keys())
        else:
            for p in self.player[player_idx].team:
                candidates += PokeDB.jpn_to_foreign_labels[p.label]

        s = ut.OCR(img1, lang='all', candidates=candidates,
                   log_dir=OCR_LOG_DIR / "display_name")
        display_name = PokeDB.foreign_to_jpn_label[s]  # 和訳

        if not self.mute:
            print(f"\t名前 {display_name}")

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
                print(f"\tHP {hp}")
        else:
            warnings.warn(f"HP must be a number : {s}")
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
            print(f"\tHP {int(rhp*100):.1f}%")

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
                    print(f"\t状態異常 {ailment}")
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
            print(f"\t{condition}")

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
                    print(f"瀕死 {p.label}")

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
            PokeDB.label2names.keys()), log_dir=OCR_LOG_DIR / "box_name")
        name = PokeDB.label2names[display_name][0]

        # フォルム識別
        if display_name in PokeDB.form_diff:
            for s in PokeDB.label2names[display_name]:
                # タイプで識別
                if PokeDB.form_diff[display_name] == 'type':
                    types = []
                    for t in range(2):
                        img1 = ut.BGR2BIN(
                            self.img[150:190, 1335+200*t:1480+200*t], threshold=230)
                        type = ut.OCR(img1, candidates=TYPES, log_dir=OCR_LOG_DIR / "box_type")
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
            p.ability.org_name = PokeDB.home[name]['ability'][0] if name in PokeDB.home else PokeDB.zukan[name]['ability'][0]

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
        p.terastal = ut.OCR(img1, candidates=TYPES, log_dir=OCR_LOG_DIR / "box_terastal")

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
        if (p.name == 'ザシアン(れきせん)' and p.item.name == 'くちたけん') or \
                (p.name == 'ザマゼンタ(れきせん)' and p.item.name == 'くちたたて'):
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
                type[i] = ut.OCR(img1, candidates=TYPES,
                                 log_dir=OCR_LOG_DIR / "display_type")

        for name in PokeDB.label2names[display_name]:
            zukan_type = PokeDB.zukan[name]['type'].copy()

            if len(zukan_type) == 1:
                zukan_type.append('')
            if zukan_type == type or zukan_type == [type[1], type[0]]:
                return name

        warnings.warn(f"\tFailed to get a form of {display_name}")
        return ''

    def read_win_loss(self, capture: bool = True):
        """勝敗を読み取る"""
        if capture:
            self.capture()

        img1 = ut.BGR2BIN(self.img[940:1060, 400:750],
                          threshold=140, bitwise_not=True)

        for s, template in self.template_winloss.items():
            if ut.template_match_score(img1, template) > 0.99:
                print(f"ゲーム終了 {s}")
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
        if self.mode == Mode.OFFLINE:
            if 'しかけて' in worts[-1]:
                print('*'*50, '\nNew Game\n', '*'*50)
                self.init_game()
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
            dict['type'] = ut.find_most_similar(TYPES, words[1][:-4])

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
                selected, display_name=s).label
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
                if p.ability.name == 'ばけのかわ':
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
                        self.text_buffer[i-1]['move'] in PokeDB.category_to_moves['call_move']:

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
                        move.add_pp(-2 if self.pokemon[not pidx].ability.name == 'プレッシャー' else -1)

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
        self.text_buffer = new_buffer if self.mode == Mode.ONLINE else []

        # 両プレイヤーが使用した技の優先度が同じなら、行動順から素早さを推定する
        if len(move_order) == 2 and move_order[0]['move_speed'] == move_order[1]['move_speed']:

            # 相手の行動順index
            oidx = [dict['player_idx'] for dict in move_order].index(1)

            p = Pokemon.find(self.selected_pokemons(
                1), display_name=move_order[oidx]['display_name'])

            if p is None:
                warnings.warn(f"{move_order[oidx]['display_name']} is not in \
                              {[p.label for p in self.selected_pokemons(1)]}")
            else:
                # 相手のS補正値
                r_speed = move_order[oidx]['eff_speed'] / move_order[oidx]['speed']

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
            macro += f"{button} 0.1s\n"
            if i < n-1 and interval:
                macro += f"{interval}s\n"
        if post_sleep:
            macro += f"{post_sleep}s\n"

        # コマンド送信
        if macro:
            macro_id = NX.macro(NXID, macro, block=False)
            while macro_id not in NX.state[NXID]['finished_macros']:
                time.sleep(0.01)
