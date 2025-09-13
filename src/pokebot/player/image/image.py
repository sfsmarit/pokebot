import cv2

from pokebot.common.enums import Ailment, Condition, \
    SideField, GlobalField, Weather, Terrain
import pokebot.common.utils as ut

from .image_utils import BGR2BIN


class TemplateImage:
    @classmethod
    def init(cls):
        cls.poke_icon_template_code = {}
        with open(ut.path_str('assets', 'template', 'codelist.txt'), encoding='utf-8') as f:
            for line in f:
                data = line.split()
                cls.poke_icon_template_code[data[0]] = data[1]

        cls.phase = {}
        for x, v in zip(["standby", "selection", "action", "switch"], [100, 100, 200, 150]):
            cls.phase[x] = BGR2BIN(cv2.imread(ut.path_str("assets", "phase", f"{x}.png")), threshold=v, bitwise_not=True)

        cls.box_window = BGR2BIN(cv2.imread(ut.path_str("assets", "screen", "box_window.png")), threshold=128)
        cls.condition_window = BGR2BIN(cv2.imread(ut.path_str("assets", "screen", "condition_window.png")), threshold=200, bitwise_not=True)
        cls.fainting_symbol = BGR2BIN(cv2.imread(ut.path_str("assets", "screen", "fainting_symbol.png")), threshold=128)
        cls.win_loss = {}
        for x in ['win', 'loss']:
            cls.win_loss[x] = BGR2BIN(cv2.imread(ut.path_str("assets", "screen", f"{x}.png")), threshold=140, bitwise_not=True)

        cls.switch_state = {}
        for x in ['active', 'alive', 'fainting']:
            cls.switch_state[x] = BGR2BIN(cv2.imread(ut.path_str("assets", "switch", f"{x}.png")), threshold=150, bitwise_not=True)

        cls.condition_turns = []
        for i in range(8):
            img = BGR2BIN(cv2.imread(ut.path_str("assets", "condition", "turn", f"{i+1}.png")), threshold=128)
            if cv2.countNonZero(img)/img.size < 0.5:
                img = cv2.bitwise_not(img)
            cls.condition_turns.append(img)

        cls.condition_counts = []
        for i in range(3):
            img = BGR2BIN(cv2.imread(ut.path_str("assets", "condition", "count", f"{i+1}.png")), threshold=128)
            if cv2.countNonZero(img)/img.size < 0.5:
                img = cv2.bitwise_not(img)
            cls.condition_counts.append(img)

        cls.horobi_counts = []
        for i in range(3):
            img = BGR2BIN(cv2.imread(ut.path_str("assets", "condition", "horobi", f"{i+1}.png")), threshold=128)
            if cv2.countNonZero(img)/img.size < 0.5:
                img = cv2.bitwise_not(img)
            cls.condition_counts.append(img)

        terastal_code = {}
        with open(ut.path_str('assets', 'terastal', 'codelist.txt'), encoding='utf-8') as f:
            for line in f:
                data = line.split()
                terastal_code[data[1]] = data[0]

        cls.terastal = {}
        for s in terastal_code:
            img = BGR2BIN(cv2.imread(ut.path_str("assets", "terastal", f"{terastal_code[s]}.png")), threshold=230, bitwise_not=True)
            cls.terastal[s] = img[24:-26, 20:-22]

        cls.ailment = {}
        for x in Ailment:
            if x.value:
                cls.ailment[x] = (BGR2BIN(cv2.imread(ut.path_str("assets", "ailment", f"{x.name}.png")), threshold=200, bitwise_not=True))

        cls.condition = {}
        enum_dir = [
            (Condition, "condition"),
            (Weather, "global_field"),
            (Terrain, "global_field"),
            (GlobalField, "global_field"),
            (SideField, "side_field")
        ]
        for enum, dir in enum_dir:
            for x in enum:
                if x.name in ["NONE", "WEATHER", "TERRAIN"]:
                    continue
                img = BGR2BIN(cv2.imread(ut.path_str("assets", "condition", dir, f"{x.name}.png")), threshold=128)
                if cv2.countNonZero(img)/img.size < 0.5:
                    img = cv2.bitwise_not(img)
                cls.condition[x] = img

        cls.expirable_conditions = [x for enum in [Condition, Weather, Terrain, GlobalField, SideField]
                                    for x in enum if x.is_expirable]
        cls.accumulative_conditions = [Condition.STOCK, SideField.MAKIBISHI, SideField.DOKUBISHI]
