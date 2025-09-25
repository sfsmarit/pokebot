from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import Bot

import cv2

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Ailment, Condition, SideField
from pokebot.common.constants import TYPES, STAT_CODES
# from pokebot.common import PokeDB

from pokebot.player.image import TemplateImage, image_utils as iut


def _read_opponent_terastal(self: Bot, capture: bool = True) -> str:
    """相手の場のポケモンのテラスタイプを読み取る"""
    if capture:
        type(self).capture()
    terastal = ""
    img = iut.BGR2BIN(self.img[200:282, 810:882], threshold=230, bitwise_not=True)
    img = img[24:-26, 20:-22]
    if cv2.minMaxLoc(img)[0] == 0:  # 有色ならテラスタル発動中
        max_score = 0
        for t in TemplateImage.terastal:
            score = iut.template_match_score(img, TemplateImage.terastal[t])
            if max_score < score:
                max_score = score
                terastal = t
    if terastal:
        print(f"\t相手 {terastal}T")
    return terastal


def _read_active_label(self: Bot, idx: PlayerIndex | int, capture: bool = True):
    """場のポケモンの表示名を読み取る"""
    if capture:
        type(self).capture()
    img = iut.BGR2BIN(self.img[80:130, 160:450], threshold=200, bitwise_not=True)
    candidates = []
    if not self.online and idx == 1:
        candidates = list(PokeDB.label_to_names.keys())
    else:
        for p in self.battle.players[idx].team:
            candidates += PokeDB.jpn_to_foreign_labels[p.label]
    s = iut.OCR(img, lang='all', candidates=candidates, log_dir=type(self).ocr_log_dir / "label")
    label = PokeDB.foreign_to_jpn_label[s]  # 和訳
    print(f"\t名前 {label}")
    return label


def _read_hp(self: Bot, capture: bool = True) -> int:
    """場のポケモンの残りHPを読み取る"""
    if capture:
        type(self).capture()
    img = iut.BGR2BIN(self.img[475:515, 210:293], threshold=200, bitwise_not=False)
    s = iut.OCR(img, lang='num', log_dir=type(self).ocr_log_dir / "hp")
    if s and not s[-1].isdigit():
        s = s[:-1]
    hp = max(1, int(s)) if s.isdigit() else 1
    print(f"\tHP {hp}")
    return hp


def _read_hp_ratio(self: Bot, capture: bool = True) -> float:
    """場のポケモンのHP割合を読み取る"""
    if capture:
        type(self).capture()
    dy, dx = 46, 242
    img = iut.BGR2BIN(self.img[472:(472+dy), 179:(179+dx)], threshold=100, bitwise_not=True)
    count = 0
    for i in range(dx):
        if img.data[int(dy/2), i] == 0:
            count += 1
    hp_ratio = max(0.001, min(1, count/240))
    print(f"\tHP {int(hp_ratio*100):.1f}%")
    return hp_ratio


def _read_ailment(self: Bot, capture: bool = True) -> Ailment:
    """場のポケモンの状態異常を読み取る"""
    if capture:
        type(self).capture()
    img = iut.BGR2BIN(self.img[430:460, 270:360], threshold=200, bitwise_not=True)
    for ailment in TemplateImage.ailment:
        if iut.template_match_score(img, TemplateImage.ailment[ailment]) > 0.99:
            print(f"\t状態異常 {ailment}")
            return ailment
    return Ailment.NONE


def _read_rank(self: Bot, capture: bool = True):
    """場のポケモンの能力ランクを読み取る"""
    if capture:
        type(self).capture()
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
    if any(ranks):
        print('\t能力ランク ' + ' '.join([s + ('+' if v > 0 else '') + str(v) for s, v in zip(STAT_CODES[1:], ranks) if v]))
    return ranks


def _read_condition(self: Bot, capture: bool = True):
    """場とポケモンの状態変化を読み取る"""
    if capture:
        type(self).capture()

    dy = 86
    condition = {}

    for i in range(6):
        img = iut.BGR2BIN(self.img[188+dy*i:232+dy*i, 1190:1450], threshold=128)
        if cv2.minMaxLoc(img)[0]:
            break

        if cv2.countNonZero(img)/img.size < 0.5:
            img = cv2.bitwise_not(img)  # ハイライト状態なら色反転

        for x in TemplateImage.condition:
            if iut.template_match_score(img, TemplateImage.condition[x]) < 0.99:
                continue

            if x in TemplateImage.expirable_conditions:
                # 残りターン数を撮影
                num_img = iut.BGR2BIN(self.img[188+dy*i:232+dy*i, 1710:1733], threshold=128)
                if cv2.countNonZero(num_img)/num_img.size < 0.5:
                    num_img = cv2.bitwise_not(num_img)  # ハイライト状態なら色反転

                for j, template in enumerate(TemplateImage.condition_turns):
                    if iut.template_match_score(num_img, template) > 0.99:
                        condition[x] = j+1
                        break

                # TODO ねがいごと回復設定
                if x == SideField.WISH:
                    pass

            elif x in TemplateImage.accumulative_conditions:
                # カウントを撮影
                num_img = iut.BGR2BIN(self.img[188+dy*i:232+dy*i, 1738:1766], threshold=128)
                if cv2.countNonZero(num_img)/num_img.size < 0.5:
                    num_img = cv2.bitwise_not(num_img)  # ハイライト状態なら色反転

                for j, template in enumerate(TemplateImage.condition_counts):
                    if iut.template_match_score(num_img, template) > 0.99:
                        condition[x] = j+1
                        break

            elif x == Condition.HOROBI:
                # カウントを撮影
                num_img = iut.BGR2BIN(self.img[188+dy*i:232+dy*i, 1725:1755], threshold=128)
                if cv2.countNonZero(num_img)/num_img.size < 0.5:
                    num_img = cv2.bitwise_not(num_img)

                for j, template in enumerate(TemplateImage.horobi_counts):
                    if iut.template_match_score(num_img, template) > 0.99:
                        condition[x] = j+1
                        break
            else:
                condition[x] = 1

            break

    if condition:
        print(f"\t{condition}")

    return condition


def _read_item(self: Bot, capture: bool = True) -> str:
    """場のポケモンのアイテムを読み取る"""
    if capture:
        type(self).capture()
    img = iut.BGR2BIN(self.img[350:395, 470:760], threshold=230, bitwise_not=True)
    return iut.OCR(img, candidates=PokeDB.items() + [''], log_dir=type(self).ocr_log_dir / "item")


def _read_form(self: Bot, label: str, capture: bool = True) -> str:
    """場のポケモンのフォルムを読み取る"""
    if label not in ['ウーラオス', 'ケンタロス', 'ザシアン', 'ザマゼンタ']:
        return ''

    if capture:
        type(self).capture()

    types = ['']*2
    dx = 210

    for i in range(2):
        img = iut.BGR2BIN(self.img[170:210, 525+dx*i:665+dx*i], threshold=230, bitwise_not=True)
        if cv2.minMaxLoc(img)[0] == 255:
            types[i] = ''
        else:
            types[i] = iut.OCR(img, candidates=TYPES, log_dir=type(self).ocr_log_dir / "display_type")

    for name in PokeDB.label_to_names[label]:
        zukan_type = PokeDB.zukan[name].types.copy()
        if len(zukan_type) == 1:
            zukan_type.append('')
        if zukan_type == types or zukan_type == [types[1], types[0]]:
            return name

    print(f"\tFailed to get a form of {label}")
    return ""


def _read_fainting_opponent(self: Bot, capture: bool = True):
    """パーティ確認画面で相手のポケモンが瀕死かどうか確認する"""
    if capture:
        type(self).capture()
    dy = 102
    for i, poke in enumerate(self.battle.players[1].team):
        img = iut.BGR2BIN(self.img[280+dy*i:302+dy*i, 1314:1334], threshold=128)
        if iut.template_match_score(img, TemplateImage.fainting_symbol) > 0.99:
            self.battle.selection_indexes[1].append(i)  # 出オチした相手ポケモンを選出に追加
            poke.hp = 0
            poke.observed = True  # 観測
            print(f"瀕死 {poke.label}")
