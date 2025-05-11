from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN
from copy import deepcopy
import requests
import glob
import os
import glob
import jaconv
import unicodedata
from importlib import resources
from pathlib import Path
from datetime import datetime, timedelta, timezone
from PIL import Image
import cv2
import Levenshtein
import pyocr
import pyocr.builders


def selective_deepcopy(old, new, keys_to_deepcopy: list[str] = []):
    for key, val in old.__dict__.items():
        if key in keys_to_deepcopy:
            setattr(new, key, deepcopy(val))
        else:
            setattr(new, key, recursive_copy(val))


def recursive_copy(obj):
    if isinstance(obj, list):
        return [recursive_copy(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: recursive_copy(v) for k, v in obj.items()}
    else:
        return obj


def path(*path_parts: str):
    return resources.files("pokebot").joinpath(*path_parts)


def path_str(*path_parts: str):
    return str(resources.files("pokebot").joinpath(*path_parts))


def download(url, dst):
    print(f"Downloading {url}")
    res = requests.get(url)
    with open(dst, 'w', encoding='utf-8') as fout:
        fout.write(res.text)


def current_season() -> int:
    dt_now = datetime.now(timezone(timedelta(hours=+9), 'JST'))
    y, m, d = dt_now.year, dt_now.month, dt_now.day
    return max(12*(y-2022) + m - 11 - (d == 1), 1)


def regulation(filename: str, season: int | None = None) -> str:
    if not season:
        season = current_season()
    with open(filename, encoding='utf-8', newline='\r\n') as f:
        for line in f:
            data = line.split()
            if int(data[0]) == season:
                return data[1]
    return 'G'


def round_half_up(v: float) -> int:
    """四捨五入"""
    return int(Decimal(str(v)).quantize(Decimal('0'), rounding=ROUND_HALF_UP))


def round_half_down(v: float) -> int:
    """五捨五超入"""
    return int(Decimal(str(v)).quantize(Decimal('0'), rounding=ROUND_HALF_DOWN))


def frac(v: float) -> float:
    """小数部分"""
    return v - int(v)


def box_trim(img, threshold=255):
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


def cv2pil(image):
    new_image = image.copy()
    if new_image.ndim == 2:  # モノクロ
        pass
    elif new_image.shape[2] == 3:  # カラー
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGR2RGB)
    elif new_image.shape[2] == 4:  # 透過
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGRA2RGBA)
    new_image = Image.fromarray(new_image)
    return new_image


def BGR2BIN(img, threshold=128, bitwise_not=False):
    img1 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, img1 = cv2.threshold(img1, threshold, 255, cv2.THRESH_BINARY)
    if bitwise_not:
        img1 = cv2.bitwise_not(img1)
    return img1


def find_most_similar(str_list, s, ignore_dakuten=False):
    """最も似ている要素を返す"""
    if s in str_list:
        return s

    s1 = jaconv.hira2kata(s)
    if ignore_dakuten:
        s1 = remove_dakuten(s1)
        str_list = list(map(remove_dakuten, str_list))

    distances = [Levenshtein.distance(s1, jaconv.hira2kata(s)) for s in str_list]

    return str_list[distances.index(min(distances))]


def template_match_score(img, template):
    """テンプレートマッチの一致度"""
    result = cv2.matchTemplate(img, template, cv2.TM_CCORR_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return max_val


def jpn_char_ratio(s):
    """日本語の文字の割合"""
    if not s:
        return 0
    bools = [any(name in unicodedata.name(c) for name in
                 ["HIRAGANA", "KATAKANA", "CJK UNIFIED"]) for c in s]
    return sum(bools)/len(bools)


def to_upper_jpn(s):
    """小文字から大文字に変換"""
    trans = str.maketrans('ぁぃぅぇぉっゃゅょァィゥェォッャュョ', 'あいうえおつやゆよアイウエオツヤユヨ')
    return s.translate(trans)


def remove_dakuten(s):
    """濁点を除去"""
    trans = str.maketrans(
        'がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポ',
        'かきくけこさしすせそたちつてとはひふへほはひふへほカキクケコサシスセソタチツテトハヒフヘホハヒフヘホ'
    )
    return s.translate(trans)


def OCR(img,
        lang: str = 'jpn',
        candidates: list[str] = [],
        log_dir: Path | None = None,
        scale: int = 1,
        ignore_dakuten: bool = False):

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
        result = find_most_similar(candidates, result, ignore_dakuten=ignore_dakuten)

    return result
