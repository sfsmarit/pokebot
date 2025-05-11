from enum import Enum, auto


class BaseEnum(Enum):
    def __str__(self):
        return str(self.value)

    @classmethod
    def names(cls) -> list[str]:
        return [x.name for x in cls]


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
    AQUA_RING = ["アクアリング", 1, True]
    AME_MAMIRE = ["あめまみれ", 3, False]
    ENCORE = ["アンコール", 3, False]
    ANTI_AIR = ["うちおとす", 1, False]
    HEAL_BLOCK = ["かいふくふうじ", 5, True]
    KANASHIBARI = ["かなしばり", 3, False]
    CRITICAL = ["急所ランク", 3, True]
    CONFUSION = ["こんらん", 5, True]
    SHIOZUKE = ["しおづけ", 1, False]
    JIGOKUZUKI = ["じごくづき", 2, False]
    CHARGE = ["じゅうでん", 1, False]
    STOCK = ["たくわえる", 3, False]
    CHOHATSU = ["ちょうはつ", 3, False]
    MAGNET_RISE = ["でんじふゆう", 5, True]
    SWITCH_BLOCK = ["にげられない", 1, False]
    NEMUKE = ["ねむけ", 2, False]
    NEOHARU = ["ねをはる", 1, False]
    NOROI = ["のろい", 1, True]
    BIND = ["バインド", 5, False]
    HOROBI = ["ほろびのうた", 3, True]
    MICHIZURE = ["みちづれ", 1, False]
    MEROMERO = ["メロメロ", 1, False]
    BAD_POISON = ["もうどく", 15, False]
    YADORIGI = ["やどりぎのタネ", 1, True]

    def __str__(self):
        return str(self.value[0])

    @property
    def max_count(self):
        return self.value[1]

    @property
    def is_baton(self):
        return self.value[2]


class GlobalField(BaseEnum):
    WEATHER = ["天候", 8]
    TERRAIN = ["フィールド", 8]
    TRICKROOM = ["トリックルーム", 5]
    GRAVITY = ["じゅうりょく", 5]

    def __str__(self):
        return self.value[0]

    @property
    def max_count(self) -> int:
        return self.value[1]


class SideField(BaseEnum):
    REFLECTOR = ["リフレクター", 8]
    LIGHTWALL = ["ひかりのかべ", 8]
    SHINPI = ["しんぴのまもり", 5]
    WHITE_MIST = ["しろいきり", 5]
    OIKAZE = ["おいかぜ", 3]
    WISH = ["ねがいごと", 2]
    MAKIBISHI = ["まきびし", 3]
    DOKUBISHI = ["どくびし", 2]
    STEALTH_ROCK = ["ステルスロック", 1]
    NEBA_NET = ["ねばねばネット", 1]

    def __str__(self):
        return self.value[0]

    @property
    def max_count(self) -> int:
        return self.value[1]


class Weather(BaseEnum):
    NONE = None
    SUNNY = "はれ"
    RAINY = "あめ"
    SNOW = "ゆき"
    SAND = "すなあらし"


class Terrain(BaseEnum):
    NONE = None
    ELEC = "エレキフィールド"
    GRASS = "グラスフィールド"
    PSYCO = "サイコフィールド"
    MIST = "ミストフィールド"


class MoveCategory(BaseEnum):
    NONE = None
    PHY = "物理"
    SPE = "特殊"
    STA = "変化"


class BoostSource(BaseEnum):
    """能力ブーストのトリガー"""
    NONE = None
    ABILITY = auto()
    ITEM = auto()
    WEATHER = auto()
    FIELD = auto()


class Mode(BaseEnum):
    SIM = "Simulation"
    OFFLINE = "Offline"
    ONLINE = "Online"


class Phase(BaseEnum):
    NONE = None
    SELECTION = "選出"
    BATTLE = "バトル"
    SWITCH = "交代"


class Time(BaseEnum):
    """時間 [s]"""
    GAME = 20*60                # 試合時間
    SELECTION = 90              # 選出
    COMMAND = 45                # コマンド入力
    CAPTURE = 0.1               # キャプチャ遅延
    TRANSITION_CAPTURE = 0.3    # 画面遷移を伴うキャプチャ遅延


class Command(BaseEnum):
    SELECT_0 = ["SELECT", 0]
    SELECT_1 = ["SELECT", 1]
    SELECT_2 = ["SELECT", 2]
    SELECT_3 = ["SELECT", 3]
    SELECT_4 = ["SELECT", 4]
    SELECT_5 = ["SELECT", 5]
    SELECT_6 = ["SELECT", 6]
    SELECT_7 = ["SELECT", 7]
    SELECT_8 = ["SELECT", 8]
    SELECT_9 = ["SELECT", 9]
    SWITCH_0 = ["SWITCH", 0]
    SWITCH_1 = ["SWITCH", 1]
    SWITCH_2 = ["SWITCH", 2]
    SWITCH_3 = ["SWITCH", 3]
    SWITCH_4 = ["SWITCH", 4]
    SWITCH_5 = ["SWITCH", 5]
    SWITCH_6 = ["SWITCH", 6]
    SWITCH_7 = ["SWITCH", 7]
    SWITCH_8 = ["SWITCH", 8]
    SWITCH_9 = ["SWITCH", 9]
    MOVE_0 = ["MOVE", 0]
    MOVE_1 = ["MOVE", 1]
    MOVE_2 = ["MOVE", 2]
    MOVE_3 = ["MOVE", 3]
    MOVE_4 = ["MOVE", 4]
    MOVE_5 = ["MOVE", 5]
    MOVE_6 = ["MOVE", 6]
    MOVE_7 = ["MOVE", 7]
    MOVE_8 = ["MOVE", 8]
    MOVE_9 = ["MOVE", 9]
    TERASTAL_0 = ["TERASTAL", 0]
    TERASTAL_1 = ["TERASTAL", 1]
    TERASTAL_2 = ["TERASTAL", 2]
    TERASTAL_3 = ["TERASTAL", 3]
    TERASTAL_4 = ["TERASTAL", 4]
    TERASTAL_5 = ["TERASTAL", 5]
    TERASTAL_6 = ["TERASTAL", 6]
    TERASTAL_7 = ["TERASTAL", 7]
    TERASTAL_8 = ["TERASTAL", 8]
    TERASTAL_9 = ["TERASTAL", 9]
    # MEGAEVOL_0 = ["MEGAEVOL", 0]
    # MEGAEVOL_1 = ["MEGAEVOL", 1]
    # MEGAEVOL_2 = ["MEGAEVOL", 2]
    # MEGAEVOL_3 = ["MEGAEVOL", 3]
    # MEGAEVOL_4 = ["MEGAEVOL", 4]
    # MEGAEVOL_5 = ["MEGAEVOL", 5]
    # MEGAEVOL_6 = ["MEGAEVOL", 6]
    # MEGAEVOL_7 = ["MEGAEVOL", 7]
    # MEGAEVOL_8 = ["MEGAEVOL", 8]
    # MEGAEVOL_9 = ["MEGAEVOL", 9]
    STRUGGLE = ["STRUGGLE", 1000]   # わるあがき
    FORCED = ["FORCED", 1001]       # あばれる、行動不能など
    SKIP = ["SKIP", 1002]         # 行動スキップ
    NONE = ["NONE", 1003]

    @property
    def index(self) -> int:
        return self.value[1]

    @property
    def is_switch(self) -> bool:
        return self.value[0] == "SWITCH"

    @property
    def is_move(self) -> bool:
        return self.value[0] == "MOVE"

    @property
    def is_terastal(self) -> bool:
        return self.value[0] == "TERASTAL"

    @property
    def is_megaevol(self) -> bool:
        return self.value[0] == "MEGAEVOL"

    @property
    def is_battle(self) -> bool:
        return self.value[0] in ["MOVE", "TERASTAL", "MEGAEVOL"]

    @classmethod
    def selection_commands(cls):
        return [x for x in cls if x.value[0] == "SELECT" in x.name]

    @classmethod
    def switch_commands(cls):
        return [x for x in cls if x.value[0] == "SWITCH" in x.name]

    @classmethod
    def battle_commands(cls):
        return [x for x in cls if x.value[0] not in ["SELECT", "SPECIAL"]]

    @classmethod
    def move_commands(cls):
        return [x for x in cls if "MOVE_" in x.name]

    @classmethod
    def terastal_commands(cls):
        return [x for x in cls if x.value[0] == "TERASTAL"]

    @classmethod
    def megaevol_commands(cls):
        return [x for x in cls if x.value[0] == "MEGAEVOL"]


if __name__ == "__main__":
    print(Command.move_commands)
