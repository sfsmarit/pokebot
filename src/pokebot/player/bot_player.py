import os
import sys
import time
from pathlib import Path
from importlib import resources

import cv2
import nxbt  # type: ignore

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Time, Command, Phase, Ailment, Condition, SideField, GlobalField
from pokebot.common import PokeDB
from pokebot.model import Pokemon
from pokebot.core import Battle

from .player import Player
from .image import TemplateImage
from .image import image_utils as iut

from .bot_methods.command import _input_selection_command, _input_move_command, _input_switch_command
from .bot_methods.read_opponent_team import _read_opponent_team
from .bot_methods.read_banmen import _read_banmen
from .bot_methods.read_banmen_methods import _read_opponent_terastal, _read_active_label, _read_hp, \
    _read_hp_ratio, _read_ailment, _read_rank, _read_condition, _read_item, _read_form, _read_fainting_opponent
from .bot_methods.read_pokemon_in_box import _read_pokemon_from_box
from .bot_methods.read_screen_text import _read_screen_text
from .bot_methods.read_ability_text import _read_ability_text
from .bot_methods.process_text_buffer import _process_text_buffer

# TODO sys.path.appendで実装
os.environ["PATH"] += os.pathsep + str(resources.files("pokebot.Tesseract-OCR"))
os.environ["TESSDATA_PREFIX"] = str(resources.files("pokebot.Tesseract-OCR").joinpath("tessdata"))


class BotPlayer(Player):
    cap: cv2.VideoCapture
    nx: nxbt.Nxbt
    nxid: int
    ocr_log_dir: Path = Path(sys.argv[0]).resolve().parent / 'ocr_log'

    def __init__(self):
        super().__init__()

        self.battle: Battle
        self.online: bool
        self.text_buffer: list = []
        self.recognized_labels: list[str] = []
        self.nonephase_start_time: float = 0.

    @classmethod
    def init(cls, video_id: int):
        # キャプチャ設定
        print(f"{'-'*50}\nキャプチャデバイスを接続中 {video_id=} ...")
        print("\t'v4l2-ctl --list-devices' コマンドで確認可能\n")
        cls.cap = cv2.VideoCapture(video_id)
        cls.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cls.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cls.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        print('nxbtを接続中...')
        cls.nx = nxbt.Nxbt()
        cls.nxid = cls.nx.create_controller(
            nxbt.PRO_CONTROLLER,
            reconnect_address=cls.nx.get_switch_addresses(),
        )
        cls.nx.wait_for_connection(cls.nxid)
        print(f"{'-'*50}")

    @classmethod
    def capture(cls, filename: str = ""):
        for _ in range(2):  # バッファ対策で2回撮影
            _, cls.img = cls.cap.read()
        if filename:
            cv2.imwrite(filename, cls.img)
        return cls.img

    @classmethod
    def press_button(cls, button, n=1, interval=0.1, post_sleep=0.1):
        # マクロ作成
        macro = ''
        for i in range(n):
            macro += f"{button} 0.1s\n"
            if i < n-1 and interval:
                macro += f"{interval}s\n"
        if post_sleep:
            macro += f"{post_sleep}s\n"
        # コマンド送信
        if macro:
            macro_id = cls.nx.macro(cls.nxid, macro, block=False)
            while macro_id not in cls.nx.state[cls.nxid]['finished_macros']:
                time.sleep(0.01)

    def game(self,
             opponent: Player,
             seed: int | None = None,
             online: bool = True) -> Battle:

        if seed is None:
            seed = int(time.time())

        self.online = online

        # レベルを50に修正
        if online:
            for p in self.team:
                p.level = 50

        self.battle = Battle(self, opponent, n_selection=3, seed=seed)

        # オフラインでは全員選出
        if not self.online:
            self.battle.selection_indexes[0][:len(self.team)]

        # 戦績の更新
        self.n_game += 1
        opponent.n_game += 1

        if self.battle.winner() == 0:
            self.n_won += 1
        else:
            opponent.n_won += 1

        self.update_rating(opponent, won=(self.battle.winner() == 0))  # type: ignore

        return self.battle

    def _input_selection_command(self, commands: list[Command]) -> list[int]:
        return _input_selection_command(self, commands)

    def _input_action_command(self, command: Command) -> bool:
        if command == Command.STRUGGLE:
            type(self).press_button('A', n=5)
            return True
        elif command.is_switch:
            # 交代画面に移動
            while True:
                if (pos := self._action_cursor_position()) == 1:
                    break
                delta = 1 - pos
                button = 'DPAD_DOWN' if delta > 0 else 'DPAD_UP'
                type(self).press_button(button, n=abs(delta), post_sleep=Time.TRANSITION_CAPTURE.value)
                if self._read_phase() != Phase.ACTION:
                    return False
            type(self).press_button('A', post_sleep=0.5)

            if self._is_switch_window():
                return self._input_switch_command(command)
        else:
            return _input_move_command(self, command)

        return False

    def _input_switch_command(self, command: Command) -> bool:
        return _input_switch_command(self, command)

    def _read_phase(self, capture: bool = True) -> Phase:
        if self._is_action_window(capture=capture):
            self.phase = Phase.ACTION
        elif self._is_switch_window(capture=False):
            self.phase = Phase.SWITCH
        elif self._is_selection_window(capture=False):
            self.phase = Phase.SELECTION
        elif self._is_standby_window(capture=False):
            self.phase = Phase.STAND_BY
        else:
            self.phase = Phase.NONE
        return self.phase

    def _is_standby_window(self, capture: bool = True) -> bool:
        """オンライン対戦の待機画面ならTrue"""
        if capture:
            type(self).capture()
        img = iut.BGR2BIN(self.img[10:70, 28:88], threshold=100, bitwise_not=True)
        return iut.template_match_score(img, TemplateImage.phase["standby"]) > 0.99

    def _is_selection_window(self, capture: bool = True) -> bool:
        """選出画面ならTrue"""
        if capture:
            type(self).capture()
        img = iut.BGR2BIN(self.img[14:64, 856:906], threshold=100, bitwise_not=True)
        return iut.template_match_score(img, TemplateImage.phase["selection"]) > 0.99

    def _is_action_window(self, capture: bool = True) -> bool:
        """ターン開始時の画面ならTrue"""
        if capture:
            type(self).capture()
        img = iut.BGR2BIN(self.img[997:1039, 827:869], threshold=200, bitwise_not=True)
        # 黄色点滅時にも読み取れるように閾値を下げている
        return iut.template_match_score(img, TemplateImage.phase["action"]) > 0.95

    def _is_switch_window(self, capture: bool = True) -> bool:
        """交代画面ならTrue"""
        if capture:
            type(self).capture()
        img = iut.BGR2BIN(self.img[140:200, 770:860], threshold=150, bitwise_not=True)
        return iut.template_match_score(img, TemplateImage.phase["switch"]) > 0.99

    def _is_condition_window(self, capture: bool = True) -> bool:
        """場の状態の確認画面ならTrue"""
        if capture:
            type(self).capture()
        img = iut.BGR2BIN(self.img[76:132, 1112:1372], threshold=200, bitwise_not=True)
        return iut.template_match_score(img, TemplateImage.condition_window) > 0.99

    def _selection_cursor_position(self, capture: bool = True) -> int:
        if capture:
            type(self).capture()
        for i in range(6):
            img = cv2.cvtColor(self.img[200+116*i:250+116*i, 500:550], cv2.COLOR_BGR2GRAY)
            if img[0, 0] > 150:
                return i
        return 6

    def _action_cursor_position(self, capture: bool = True) -> int:
        """行動選択画面でのカーソル位置
            オンライン -> 0: たたかう, 1:ポケモン, 2:にげる
            オフライン -> 0: たたかう, 1:ポケモン, 2:バッグ, 3:にげる
        """
        if capture:
            type(self).capture()
        y0 = 788 if self.online else 700
        for i in range(4):
            img = cv2.cvtColor(self.img[y0+88*i:y0+88*i+70, 1800:1850], cv2.COLOR_BGR2GRAY)
            if img[0, 0] > 150:
                return i
        return 0

    def _move_cursor_position(self, capture: bool = True) -> int:
        """技選択画面でのカーソル位置"""
        if capture:
            type(self).capture()
        for i in range(4):
            img = cv2.cvtColor(self.img[680+112*i:700+112*i, 1420:1470], cv2.COLOR_BGR2GRAY)
            if img[0, 0] > 150:
                return i
        return 0

    def _read_pp(self, move_idx, capture: bool = True) -> int:
        if capture:
            type(self).capture()
        for thr in [200, 150, 120]:
            img = iut.BGR2BIN(self.img[660+112*move_idx:700+112*move_idx, 1755:1800], threshold=thr, bitwise_not=True)
            s = iut.OCR(img, lang='num', log_dir=self.ocr_log_dir / "pp")
            if s and not s[-1].isdigit():
                s = s[:-1]
            if s.isdigit():
                return int(s)
        return 0

    def _read_switch_state(self, capture: bool = True) -> str:
        """交代画面でポケモンの状態(alive/fainting/in_battle)を読み取る"""
        if capture:
            type(self).capture()
        img = iut.BGR2BIN(self.img[140:200, 1060:1260], threshold=150, bitwise_not=True)
        for s, img in TemplateImage.switch_state.items():
            if iut.template_match_score(img, img) > 0.99:
                return s
        return ""

    def _read_switch_label(self, switch_idx: int, capture: bool = True) -> str:
        """交代画面で自分のポケモンの表示名を読み取る"""
        if capture:
            type(self).capture()
        img = iut.BGR2BIN(self.img[171+126*switch_idx:212+126*switch_idx, 94:300], threshold=100)
        labels = [PokeDB.jpn_to_foreign_labels[p.label] for p in self.team]
        s = iut.OCR(img, candidates=sum(labels, []), lang='all', log_dir=self.ocr_log_dir / "change_name")
        label = PokeDB.foreign_to_jpn_label[s]  # 和訳
        return label

    def _read_switch_hp(self, switch_idx: int, capture: bool = True) -> int:
        """交代画面で自分のポケモンの残りHPを読み取る"""
        if capture:
            type(self).capture()
        img = iut.BGR2BIN(self.img[232+126*switch_idx:268+126*switch_idx, 110:298], threshold=220, bitwise_not=True)
        s = iut.OCR(img, lang='eng')
        s = s[:s.find('/')].replace('T', '7')
        return int(s) if s.isdigit() else 0

    def read_team_from_box(self) -> list[Pokemon]:
        """ボックス画面からパーティを読み込む"""
        print(f"ボックス画面からポケモンを読み取り中...\n{'-'*50}")
        team = []
        # ボックスのポケモンを取得
        for i in range(6):
            type(self).capture()
            img = iut.BGR2BIN(self.img[1020:1060, 1372:1482], threshold=128)
            if iut.template_match_score(img, TemplateImage.box_window) < 0.95:
                print('Invalid screen')
                break
            team.append(self._read_pokemon_from_box())
            type(self).press_button('DPAD_DOWN', post_sleep=Time.CAPTURE.value + 0.2)
        type(self).press_button('DPAD_UP', n=len(team))  # カーソルを戻す
        return team

    def _read_pokemon_from_box(self):
        return _read_pokemon_from_box(self)

    def _read_win_loss(self, capture: bool = True) -> str | None:
        """勝敗を読み取る"""
        if capture:
            type(self).capture()
        img = iut.BGR2BIN(self.img[940:1060, 400:750], threshold=140, bitwise_not=True)
        for s, template in TemplateImage.win_loss.items():
            if iut.template_match_score(img, template) > 0.99:
                print(f"ゲーム終了 {s}")
                return s

    def _read_screen_text(self, capture: bool = True):
        return _read_screen_text(self, capture)

    def _read_ability_text(self, idx: PlayerIndex | int, capture: bool = True):
        return _read_ability_text(self, idx, capture)

    def _process_text_buffer(self):
        return _process_text_buffer(self)

    def _read_opponent_team(self, capture: bool = True):
        return _read_opponent_team(self, capture)

    def _read_banmen(self) -> bool:
        return _read_banmen(self)

    def _read_opponent_terastal(self, capture: bool = True) -> str:
        return _read_opponent_terastal(self, capture)

    def _read_active_label(self, idx: PlayerIndex | int, capture: bool = True):
        return _read_active_label(self, idx, capture)

    def _read_hp(self, capture: bool = True) -> int:
        return _read_hp(self, capture)

    def _read_hp_ratio(self, capture: bool = True) -> float:
        return _read_hp_ratio(self, capture)

    def _read_ailment(self, capture: bool = True) -> Ailment:
        return _read_ailment(self, capture)

    def _read_rank(self, capture: bool = True):
        return _read_rank(self, capture)

    def _read_condition(self, capture: bool = True):
        return _read_condition(self, capture)

    def _read_item(self, capture: bool = True):
        return _read_item(self, capture)

    def _read_form(self, label: str, capture: bool = True) -> str | None:
        return _read_form(self, label, capture)

    def _read_fainting_opponent(self, capture: bool = True):
        return _read_fainting_opponent(self, capture)

    def _overwrite_condition(self, idx: PlayerIndex | int, count: dict):
        if SideField.AURORA_VEIL.name in count:
            # オーロラベールを両壁に書き換える
            count[SideField.REFLECTOR] = count[SideField.AURORA_VEIL]
            count[SideField.LIGHTWALL] = count[SideField.AURORA_VEIL]

        poke_mgr = self.battle.poke_mgrs[idx]
        for cond in count:
            if cond in [Condition.BAD_POISON]:
                poke_mgr.add_condition_count(cond, +1)
            elif cond in [Condition.BIND, Condition.CONFUSION]:
                poke_mgr.add_condition_count(cond, -1)
            elif isinstance(cond, Condition):
                poke_mgr.count[cond] = count[cond]
            elif isinstance(cond, GlobalField):
                self.battle.field_mgr.count[cond] = count[cond]
            elif isinstance(cond, SideField):
                self.battle.field_mgr.count[cond][idx] = count[cond]
