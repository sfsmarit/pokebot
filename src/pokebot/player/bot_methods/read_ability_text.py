from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import Bot

from pokebot.common.types import PlayerIndex
from pokebot.common import PokeDB
import pokebot.common.utils as ut

from pokebot.player.image import image_utils as iut


def _read_ability_text(self: Bot, idx: PlayerIndex | int, capture: bool = True):
    if capture:
        type(self).capture()

    dx, dy = 1050, 44
    words = []

    # 行ごとにOCR
    for i in range(2):
        img1 = self.img[498+dy*i:540+dy*i, 300+dx*idx:600+dx*idx]
        img1 = iut.BGR2BIN(img1, threshold=250, bitwise_not=True)
        lang = 'all' if i == 0 else 'jpn'

        # 「急所」の黄色テキストを読み取るために、閾値を下げて再度OCRする
        if i == 0 and 0 not in img1:
            img1 = self.img[798+dy*i:842+dy*i, 285:1000]
            img1 = iut.BGR2BIN(img1, threshold=190, bitwise_not=True)

            # テキストがなければ中断
            if 0 not in img1:
                return False

            lang = 'jpn'

        s = iut.OCR(img1, lang=lang, log_dir=type(self).ocr_log_dir / "bottom_text")
        words += s.split()

        # 形式が不適切なら中断
        if not words or words[0][-1] != 'の':
            return False

    # 形式が不適切なら中断
    if len(words) != 2:
        return False

    dict = {
        'idx': idx,
        'label': words[0][:-1],
        'ability': ut.find_most_similar(PokeDB.abilities, words[1])
    }

    if dict not in self.text_buffer:
        self.text_buffer.append(dict)
        return True
    else:
        return False
