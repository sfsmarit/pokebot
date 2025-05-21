import glob
import os
import glob
from pathlib import Path
from PIL import Image
import cv2
import pyocr
import pyocr.builders

import pokebot.common.utils as ut


def box_trim(img, threshold: int = 255):
    """有色部分を長方形でトリム"""
    h, w = img.shape[0], img.shape[1]
    w_min, w_max, h_min, h_max = int(w*0.5), int(w*0.5), int(h*0.5), int(h*0.5)
    for h in range(len(img)):
        for w in range(len(img[0])):
            if img[h][w][0] < threshold or img[h][w][1] < threshold or img[h][w][2] < threshold:
                w_min = min(w_min, w)
                w_max = max(w_max, w)
                h_min = min(h_min, h)
                h_max = max(h_max, h)
    return img[h_min:h_max+1, w_min:w_max+1]


def cv2pil(img):
    new_img = img.copy()
    if new_img.ndim == 2:  # モノクロ
        pass
    elif new_img.shape[2] == 3:  # カラー
        new_img = cv2.cvtColor(new_img, cv2.COLOR_BGR2RGB)
    elif new_img.shape[2] == 4:  # 透過
        new_img = cv2.cvtColor(new_img, cv2.COLOR_BGRA2RGBA)
    new_img = Image.fromarray(new_img)
    return new_img


def BGR2BIN(img, threshold: int = 128, bitwise_not: bool = False):
    img1 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, img1 = cv2.threshold(img1, threshold, 255, cv2.THRESH_BINARY)
    if bitwise_not:
        img1 = cv2.bitwise_not(img1)
    return img1


def OCR(img,
        lang: str = 'jpn',
        candidates: list[str] = [],
        log_dir: Path | None = None,
        scale: int = 1,
        ignore_dakuten: bool = False) -> str:

    result = ''

    # 履歴に同じ画像があれば結果を流用する (速い)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

        # 履歴と照合
        for s in glob.glob(str(log_dir / '*')):
            template = cv2.cvtColor(cv2.imread(s), cv2.COLOR_BGR2GRAY)
            if template_match_score(img, template) > 0.99:
                result = Path(s).stem
                break

    # 履歴になければOCRする (遅い)
    if not result:
        # 言語とビルダを指定
        builder = pyocr.builders.TextBuilder(tesseract_layout=7)
        match lang:
            case 'all':
                lang = 'jpn+chi+kor+eng'  # +fra+deu'
            case 'num':
                lang = 'eng'
                builder = pyocr.builders.DigitBuilder(tesseract_layout=7)

        # 画像サイズの変更
        if scale > 1:
            img = cv2.resize(img, (img.shape[1]*scale, img.shape[0]
                             * scale), interpolation=cv2.INTER_CUBIC)

        # OCR
        tools = pyocr.get_available_tools()
        result = tools[0].image_to_string(cv2pil(img), lang=lang, builder=builder)
        # print(f'\t\tOCR: {result}')

        # 履歴に追加
        if result and log_dir:
            cv2.imwrite(str(Path(log_dir) / f"{result}.png"), img)

    if len(candidates):
        result = ut.find_most_similar(candidates, result, ignore_dakuten=ignore_dakuten)

    return result


def template_match_score(img, template):
    result = cv2.matchTemplate(img, template, cv2.TM_CCORR_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return max_val
