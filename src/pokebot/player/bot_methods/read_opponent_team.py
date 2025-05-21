from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot_player import BotPlayer

from pathlib import Path
import cv2

from pokebot.common import PokeDB
import pokebot.common.utils as ut
from pokebot.model import Pokemon

from pokebot.player.image import TemplateImage, image_utils as iut


def _read_opponent_team(self: BotPlayer, capture: bool = True):
    """選出画面で相手のパーティを読み取る"""
    if capture:
        type(self).capture()

    print('相手パーティ')

    self.battle.players[1].team.clear()
    trims = []

    # アイコン
    for i in range(6):
        y0 = 236+101*i-(i < 2)*2
        trims.append(iut.box_trim(self.img[y0:(y0+94), 1246:(1246+94)], threshold=200))
        trims[i] = cv2.cvtColor(trims[i], cv2.COLOR_BGR2GRAY)

    candidates = list(PokeDB.home.keys())
    scores, names = [0.]*6, ['']*6

    for filename in ut.path("assets", "template").glob("*.png"):  # type: ignore
        s = TemplateImage.poke_icon_template_code[Path(filename).stem]
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
            score = iut.template_match_score(trims[i], cv2.resize(template, (w, ht)))
            if scores[i] < score:
                scores[i] = score
                names[i] = s

    # 相手のパーティに追加
    for i, name in enumerate(names):
        # 名前の修正
        if 'イルカマン' in name:
            name = 'イルカマン(ナイーブ)'

        # ポケモンを追加
        self.battle.players[1].team.append(Pokemon(name))
        print(f"\t{i+1}: {name}")

    # 性別
    # for i in range(6):
    #    y0 = 250+101*i
    #    img1 = self.img[y0:(y0+94), 1400:(1500)]
    #    cv2.imwrite(f"{OCR_LOG_DIR}/trim_{i}.png", img1)
    #    img1 = cv2.cvtColor(trims[i], cv2.COLOR_BGR2GRAY)
