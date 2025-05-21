from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot_player import BotPlayer

from pokebot.common.constants import TYPES, NATURE_MODIFIER
from pokebot.common.enums import Gender
from pokebot.common import PokeDB
from pokebot.model import Pokemon, Item, Move

from ..image_utils import BGR2BIN, OCR


def _read_pokemon_from_box(self: BotPlayer):
    """ボックスのidx番目のポケモンを読み込む"""
    type(self).capture()

    # 特性：フォルムの識別に使うため先に読み込む
    img = BGR2BIN(self.img[580:620, 1455:1785], threshold=180, bitwise_not=True)
    ability_name = OCR(img, candidates=PokeDB.abilities, log_dir=type(self).ocr_log_dir / "box_ability")

    # 名前
    img = BGR2BIN(self.img[90:130, 1420:1620], threshold=180, bitwise_not=True)
    label = OCR(img, candidates=list(PokeDB.label_to_names.keys()), log_dir=type(self).ocr_log_dir / "box_name")
    name = PokeDB.label_to_names[label][0]

    # フォルム識別
    if label in PokeDB.form_diff:
        for s in PokeDB.label_to_names[label]:
            # タイプで識別
            if PokeDB.form_diff[label] == 'type':
                types = []
                for t in range(2):
                    img = BGR2BIN(
                        self.img[150:190, 1335+200*t:1480+200*t], threshold=230)
                    t = OCR(img, candidates=TYPES, log_dir=type(self).ocr_log_dir / "box_type")
                    types.append(t)
                if types == PokeDB.zukan[s].types or [types[1], types[0]] == PokeDB.zukan[s].types:
                    name = s
                    break
            # 特性で識別
            elif PokeDB.form_diff[label] == 'ability' and ability_name in PokeDB.zukan[s].abilities:
                name = s
                break

    # ポケモンの生成
    poke = Pokemon(name)
    poke.ability = ability_name

    # 特性の修正
    if poke.ability.name not in PokeDB.zukan[name].abilities:
        if name in PokeDB.home:
            poke.ability = PokeDB.home[name].abilities[0]
        else:
            poke.ability = PokeDB.zukan[name].abilities[0]

    # 性格
    x = [1590, 1689, 1689, 1491, 1491, 1590]
    y = [267, 321, 437, 321, 437, 491]
    modifier = [1.]*6
    for j in range(6):
        if self.img[y[j], x[j]][2] < 50:
            modifier[j] = 0.9
        elif self.img[y[j], x[j]][1] < 80:
            modifier[j] = 1.1
    for nature in NATURE_MODIFIER:
        if modifier == NATURE_MODIFIER[nature]:
            poke.nature = nature
            break

    # もちもの
    img = BGR2BIN(self.img[635:685, 1455:1785], threshold=180, bitwise_not=True)
    poke.item = Item(OCR(img, candidates=PokeDB.items() + [''], log_dir=type(self).ocr_log_dir / "box_item"))

    # テラスタイプ
    x0 = 1535+200*(len(poke._types)-1)
    img = BGR2BIN(self.img[154:186, x0:x0+145], threshold=240, bitwise_not=True)
    poke.terastal = OCR(img, candidates=TYPES, log_dir=type(self).ocr_log_dir / "box_terastal")

    # 技
    poke.moves.clear()
    for j in range(4):
        img = BGR2BIN(self.img[700+60*j:750+60*j, 1320:1570], threshold=180, bitwise_not=True)
        move = OCR(img, candidates=list(PokeDB.move_data.keys()) + [''], log_dir=type(self).ocr_log_dir / "box_move")
        poke.moves.append(Move(move))

    # レベル
    img = BGR2BIN(self.img[25:55, 1775:1830], threshold=180, bitwise_not=True)
    poke.level = int(OCR(img, log_dir=type(self).ocr_log_dir / "box_level/", lang='num').replace('.', ''))

    # 性別
    if self.img[40, 1855][0] > 180:
        poke.gender = Gender.MALE
    elif self.img[40, 1855][1] < 100:
        poke.gender = Gender.FEMALE
    else:
        poke.gender = Gender.NONE

    # ステータス
    x = [1585, 1710, 1710, 1320, 1320, 1585]
    y = [215, 330, 440, 330, 440, 512]
    stats = [0]*6

    for j in range(6):
        img = BGR2BIN(self.img[y[j]:y[j]+45, x[j]:x[j]+155], threshold=180, bitwise_not=True)
        s = OCR(img, lang=('eng' if j == 0 else 'num'))
        if j == 0:
            s = s[s.find('/')+1:]
        stats[j] = int(s)

    poke.stats = stats

    # ザシアン・ザマゼンタの識別
    if (poke.name == 'ザシアン(れきせん)' and poke.item.name == 'くちたけん') or \
            (poke.name == 'ザマゼンタ(れきせん)' and poke.item.name == 'くちたたて'):
        poke.change_form(poke.name[:-5] + poke.item.name[-2:] + 'のおう)')
    print(poke, end='\n\n')

    return poke
