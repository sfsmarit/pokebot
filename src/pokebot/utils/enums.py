from enum import Enum, auto


class BaseEnum(Enum):
    def __str__(self):
        if isinstance(self.value, tuple):
            return self.value[0]
        else:
            return str(self.value)

    def is_none(self) -> bool:
        if isinstance(self.value, tuple):
            return self.value[0] is None
        else:
            return self.value is None

    @classmethod
    def names(cls) -> list[str]:
        return [x.name for x in cls]


class Stat(BaseEnum):
    H = ("H", 0, "HP", "HP")
    A = ("A", 1, "こうげき", "攻撃")
    B = ("B", 2, "ぼうぎょ", "防御")
    C = ("C", 3, "とくこう", "特攻")
    D = ("D", 4, "とくぼう", "特防")
    S = ("S", 5, "すばやさ", "素早さ")
    ACC = ("命中", 6, "めいちゅう", "命中")
    EVA = ("回避", 7, "かいひ", "回避")

    @property
    def idx(self) -> int:
        return self.value[1]


class Gender(BaseEnum):
    NONE = None
    MALE = "オス"
    FEMALE = "メス"


class Ailment(BaseEnum):
    NONE = None
    PSN = "どく"
    PAR = "まひ"
    BRN = "やけど"
    SLP = "ねむり"
    FLZ = "こおり"


class Condition(BaseEnum):
    AQUA_RING = ("アクアリング", 1, True, False)
    AME_MAMIRE = ("あめまみれ", 3, False, True)
    ENCORE = ("アンコール", 3, False, True)
    GROUNDED = ("うちおとす", 1, False, False)
    HEAL_BLOCK = ("かいふくふうじ", 5, True, True)
    KANASHIBARI = ("かなしばり", 3, False, True)
    CRITICAL = ("急所ランク", 3, True, False)
    CONFUSION = ("こんらん", 5, True, True)
    SHIOZUKE = ("しおづけ", 1, False, False)
    JIGOKUZUKI = ("じごくづき", 2, False, True)
    CHARGE = ("じゅうでん", 1, False, False)
    STOCK = ("たくわえる", 3, False, False)
    CHOHATSU = ("ちょうはつ", 3, False, True)
    MAGNET_RISE = ("でんじふゆう", 5, True, True)
    SWITCH_BLOCK = ("にげられない", 1, False, False)
    NEMUKE = ("ねむけ", 2, False, True)
    NEOHARU = ("ねをはる", 1, False, False)
    NOROI = ("のろい", 1, True, False)
    BIND = ("バインド", 5, False, True)
    HOROBI = ("ほろびのうた", 3, True, True)
    MICHIZURE = ("みちづれ", 1, False, False)
    MEROMERO = ("メロメロ", 1, False, False)
    BAD_POISON = ("もうどく", 15, False, False)
    YADORIGI = ("やどりぎのタネ", 1, True, False)

    @property
    def max_count(self) -> int:
        return self.value[1]

    @property
    def inheritable(self) -> bool:
        return self.value[2]

    @property
    def expirable(self) -> bool:
        return self.value[3]


class GlobalField(BaseEnum):
    WEATHER = ("天候", 8, False)
    TERRAIN = ("フィールド", 8, False)
    TRICKROOM = ("トリックルーム", 5, True)
    GRAVITY = ("じゅうりょく", 5, True)

    @property
    def max_count(self) -> int:
        return self.value[1]

    @property
    def expirable(self) -> bool:
        return self.value[2]


class Weather(BaseEnum):
    NONE = (None, False)
    SUNNY = ("はれ", True)
    RAINY = ("あめ", True)
    SNOW = ("ゆき", True)
    SAND = ("すなあらし", True)

    @property
    def expirable(self) -> bool:
        return self.value[1]


class Terrain(BaseEnum):
    NONE = (None, False)
    ELEC = ("エレキフィールド", True)
    GRASS = ("グラスフィールド", True)
    PSYCO = ("サイコフィールド", True)
    MIST = ("ミストフィールド", True)

    @property
    def expirable(self) -> bool:
        return self.value[1]


class SideField(BaseEnum):
    REFLECTOR = ("リフレクター", 8, True)
    LIGHT_WALL = ("ひかりのかべ", 8, True)
    AURORA_VEIL = ("オーロラベール", 8, True)
    SHINPI = ("しんぴのまもり", 5, True)
    WHITE_MIST = ("しろいきり", 5, True)
    OIKAZE = ("おいかぜ", 3, True)
    WISH = ("ねがいごと", 2, True)
    MAKIBISHI = ("まきびし", 3, False)
    DOKUBISHI = ("どくびし", 2, False)
    STEALTH_ROCK = ("ステルスロック", 1, False)
    NEBA_NET = ("ねばねばネット", 1, False)

    @property
    def max_count(self) -> int:
        return self.value[1]

    @property
    def expirable(self) -> bool:
        return self.value[2]


class MoveCategory(BaseEnum):
    NONE = None
    PHY = "物理"
    SPE = "特殊"
    STA = "変化"


class BoostSource(BaseEnum):
    """能力ブーストの発動要因"""
    NONE = None
    ABILITY = auto()
    ITEM = auto()
    WEATHER = auto()
    FIELD = auto()


class Time(BaseEnum):
    """時間 [s]"""
    GAME = 20*60                # 試合
    SELECTION = 90              # 選出
    COMMAND = 45                # コマンド入力
    CAPTURE = 0.1               # キャプチャ遅延
    TRANSITION_CAPTURE = 0.3    # 画面遷移を伴うキャプチャ遅延
    TIMEOUT = 60                # 実機対戦でのタイムアウト


class Command(BaseEnum):
    NONE = None
    STRUGGLE = auto()
    FORCED = auto()
    SKIP = auto()
    SELECT_0 = auto()
    SELECT_1 = auto()
    SELECT_2 = auto()
    SELECT_3 = auto()
    SELECT_4 = auto()
    SELECT_5 = auto()
    SELECT_6 = auto()
    SELECT_7 = auto()
    SELECT_8 = auto()
    SELECT_9 = auto()
    SWITCH_0 = auto()
    SWITCH_1 = auto()
    SWITCH_2 = auto()
    SWITCH_3 = auto()
    SWITCH_4 = auto()
    SWITCH_5 = auto()
    SWITCH_6 = auto()
    SWITCH_7 = auto()
    SWITCH_8 = auto()
    SWITCH_9 = auto()
    MOVE_0 = auto()
    MOVE_1 = auto()
    MOVE_2 = auto()
    MOVE_3 = auto()
    MOVE_4 = auto()
    MOVE_5 = auto()
    MOVE_6 = auto()
    MOVE_7 = auto()
    MOVE_8 = auto()
    MOVE_9 = auto()
    TERASTAL_0 = auto()
    TERASTAL_1 = auto()
    TERASTAL_2 = auto()
    TERASTAL_3 = auto()
    TERASTAL_4 = auto()
    TERASTAL_5 = auto()
    TERASTAL_6 = auto()
    TERASTAL_7 = auto()
    TERASTAL_8 = auto()
    TERASTAL_9 = auto()
    MEGAEVOL_0 = auto()
    MEGAEVOL_1 = auto()
    MEGAEVOL_2 = auto()
    MEGAEVOL_3 = auto()
    MEGAEVOL_4 = auto()
    MEGAEVOL_5 = auto()
    MEGAEVOL_6 = auto()
    MEGAEVOL_7 = auto()
    MEGAEVOL_8 = auto()
    MEGAEVOL_9 = auto()
    GIGAMAX_0 = auto()
    GIGAMAX_1 = auto()
    GIGAMAX_2 = auto()
    GIGAMAX_3 = auto()
    GIGAMAX_4 = auto()
    GIGAMAX_5 = auto()
    GIGAMAX_6 = auto()
    GIGAMAX_7 = auto()
    GIGAMAX_8 = auto()
    GIGAMAX_9 = auto()
    ZMOVE_0 = auto()
    ZMOVE_1 = auto()
    ZMOVE_2 = auto()
    ZMOVE_3 = auto()
    ZMOVE_4 = auto()
    ZMOVE_5 = auto()
    ZMOVE_6 = auto()
    ZMOVE_7 = auto()
    ZMOVE_8 = auto()
    ZMOVE_9 = auto()

    def __str__(self):
        return self.name

    @property
    def idx(self) -> int:
        return int(self.name[-1])

    def is_select(self) -> bool:
        return self.name[:-2] == "SELECT"

    def is_switch(self) -> bool:
        return self.name[:-2] == "SWITCH"

    def is_move(self) -> bool:
        return self.name[:-2] == "MOVE"

    def is_terastal(self) -> bool:
        return self.name[:-2] == "TERASTAL"

    def is_megaevol(self) -> bool:
        return self.name[:-2] == "MEGAEVOL"

    def is_gigamax(self) -> bool:
        return self.name[:-2] == "GIGAMAX"

    def is_zmove(self) -> bool:
        return self.name[:-2] == "ZMOVE"

    def is_action(self) -> bool:
        return self.is_move() or self.is_terastal() or \
            self.is_megaevol() or self.is_gigamax() or self.is_zmove()

    @classmethod
    def selection_commands(cls):
        return [x for x in cls if x.is_select()]

    @classmethod
    def switch_commands(cls):
        return [x for x in cls if x.is_switch()]

    @classmethod
    def action_commands(cls):
        return [x for x in cls if x.is_action()]

    @classmethod
    def move_commands(cls):
        return [x for x in cls if x.is_move()]

    @classmethod
    def terastal_commands(cls):
        return [x for x in cls if x.is_terastal()]

    @classmethod
    def megaevol_commands(cls):
        return [x for x in cls if x.is_megaevol()]

    @classmethod
    def gigamax_commands(cls):
        return [x for x in cls if x.is_gigamax()]

    @classmethod
    def zmove_commands(cls):
        return [x for x in cls if x.is_zmove()]
