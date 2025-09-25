from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import Bot

import cv2
import unicodedata

from pokebot.common.constants import TYPES, STAT_CODES_HIRAGANA, STAT_CODES_KANJI
# from pokebot.common import PokeDB
import pokebot.common.utils as ut
from pokebot.model import Pokemon, Item, Move
from pokebot.core.move_utils import move_speed

from pokebot.player.image import image_utils as iut


def _read_screen_text(self: Bot, capture: bool = True) -> bool:
    if capture:
        type(self).capture()
    words = []

    # 文字領域にハッチがかかっていなければ中断
    img = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
    if img[790, 1300] > 190:
        return False

    # 行ごとにOCR
    dy = 63
    for i in range(2):
        img = self.img[798+dy*i:842+dy*i, 285:1400]
        img = iut.BGR2BIN(img, threshold=250, bitwise_not=True)
        lang = 'all' if i == 0 else 'jpn'

        # 枠内に白文字が含まれていなければ
        # 「急所」の黄文字を狙って再OCR
        if (re_ocr := i == 0 and 0 not in img):
            img = self.img[798+dy*i:842+dy*i, 285:1000]
            img = iut.BGR2BIN(img, threshold=190, bitwise_not=True)
            lang = 'jpn'

        # 二値化後に黒いピクセルがなければ中断
        if 0 not in img:
            return False

        s = iut.OCR(img, lang=lang, log_dir=type(self).ocr_log_dir / "bottom_text")

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

    print(f"\t{words=}")

    # 形式が不適切なら中断
    if len(words) < 2:
        return False

    # 濁点・半濁点なし
    worts = list(map(ut.remove_dakuten, words))

    # 学校最強大会の試合開始判定
    if not self.online and 'しかけて' in worts[-1]:
        self.battle._winner = 0
        return True

    # 急所
    if any(s in worts[0] for s in ['急', '所']):
        if self.text_buffer and 'move' in self.text_buffer[-1]:
            self.text_buffer[-1]['critical'] = True
        return False

    # 対象のプレイヤーを識別
    idx = 0
    if any(s in worts[0] for s in ['相', '手']):
        idx = 1
        words.pop(0)
        worts.pop(0)

    # 形式が不適切なら中断
    if len(words) < 2 or len(words[0]) < 3 or len(words[1]) < 3:
        return False

    dict = {'idx': idx, 'label': words[0][:-1]}

    # 技外し
    if '当' in worts[1]:
        if self.text_buffer and 'move' in self.text_buffer[-1]:
            self.text_buffer[-1]['hit'] = False
        return False

    if 'たせな' in worts[-1]:
        # ひるみ
        dict['flinch'] = True
    elif any(s in worts[0] for s in ['収', '穫']):
        # しゅうかく
        dict['item'] = ut.find_most_similar(PokeDB.items(), words[1][:-1])
    elif 'タイフになつ' in ''.join(worts[-2:]):
        # へんげんじざい
        dict['type'] = ut.find_most_similar(TYPES, words[1][:-4])
    elif '奪' in worts[-1]:
        # マジシャン
        dict['item'] = ut.find_most_similar(PokeDB.items(), words[1][:-1])
    elif any(s in worts[1] for s in ['コツメ', 'ヤホの', 'レンフの']):
        # ダメージアイテム
        dict['idx'] = int(not idx)
        dict['label'] = ''
        dict['item'] = ut.find_most_similar(PokeDB.items(), words[1][:-1])
    elif '少' in worts[-1]:
        # いのちのたま
        dict['item'] = 'いのちのたま'
    elif 'ノーマル' in worts[0] and '強' in words[-1]:
        # ノーマルジュエル
        dict['lost_item'] = 'ノーマルジュエル'
    elif 'ふうせんか' in worts[1]:
        # ふうせん破壊
        dict['lost_item'] = 'ふうせん'
    elif '高' in worts[-1]:
        # ブーストエナジー
        labels = STAT_CODES_HIRAGANA + STAT_CODES_KANJI
        s = ut.find_most_similar(labels, words[1][:-1])
        dict['boost_idx'] = labels.index(s) % 5 + 1
    elif '手' in worts[-1]:
        # トリック
        dict['item'] = ut.find_most_similar(PokeDB.items(), words[1][:-1])
    elif '投' in worts[-1]:
        # 投げつける
        dict['lost_item'] = ut.find_most_similar(PokeDB.items(), words[1][:-1])
    elif 'をはたき' in ''.join(worts[-2:]):
        # はたきおとす(自分が使用した場合のみ)
        dict['idx'] = int(not idx)
        s = words[1][:-1]
        if idx == 0:
            if 'の' in s:
                s = s[s.index('の')+1:]
            else:
                return True
        # 対象のポケモンの表示名を照合
        poke = Pokemon.find_most_similar(self.battle.selected_pokemons(idx), label=s)
        if poke:
            dict['label'] = poke.label
        dict['lost_item'] = ut.find_most_similar(PokeDB.items(), words[2][:-1])
    elif any(s in words[1] for s in ['身', '代']):
        # みがわり発生・解除
        if '現' in worts[-1]:
            dict['subst'] = True
        elif '消' in worts[-1]:
            dict['subst'] = True
        else:
            return False
    elif any("CJK UNIFIED" in unicodedata.name(s) for s in words[1]):
        # 2ブロック目に漢字が含まれていたら除外
        return False
    elif any(s in worts[1] for s in ['まひ', 'やけと']) or any(s in words[-1] for s in ['眠']):
        # 状態異常
        return True
    elif worts[-1][:2] == 'なつ':
        # 状態変化
        return True
    elif 'たおれ' in worts[-1]:
        # 瀕死
        return False
    elif any(s in ''.join(words[-2:]) for s in ['効', '果']):
        # タイプ相性
        return True
    elif 'タメーシ' in ''.join(worts[-2:]) or any(s in words[-1] for s in ['体', '奪']):
        # 定数ダメージ
        return True
    elif any(s in words[0] for s in ['味', '方']):
        # 設置技
        return True
    elif any(s in worts[-1] for s in ['戻', '引', 'くり']):
        # 交代
        return True
    elif any(s in words[-1] for s in ['変', '身']):
        # 変身
        return True
    else:
        # 形式が不適切なら中断
        if worts[0][-1] not in ['の', 'は']:
            return False

        # ノイズも含めてテキスト候補を用意
        candidates = PokeDB.moves() + PokeDB.abilities
        if worts[0][-1] == 'は':
            candidates += PokeDB.items()

        s = ut.find_most_similar(candidates, words[1][:-1])

        # 技を読み取った場合
        if s in PokeDB.move_data_old:
            dict['move'] = s
            dict['hit'] = True
            dict['critical'] = False
            dict['speed'] = self.battle.pokemons[idx].stats[5]
            dict['eff_speed'] = self.battle.poke_mgrs[idx].effective_speed()
            dict['move_speed'] = move_speed(self.battle, idx, Move(s))

        # アイテムを読み取った場合
        elif s in PokeDB.item_data:
            if Item(s).consumable:
                dict['lost_item'] = s
            else:
                dict['item'] = s

    if len(dict) <= 2 or dict in self.text_buffer:
        return False

    self.text_buffer.append(dict)
    return True
