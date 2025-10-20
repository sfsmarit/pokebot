import time
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN
from copy import deepcopy
import requests
import jaconv
import unicodedata
from importlib import resources
from datetime import datetime, timedelta, timezone
import Levenshtein


def timer(func, *args, **kwargs) -> None:
    t0 = time.time()
    func(*args, **kwargs)
    print(f"{func.__name__} {(time.time()-t0)*1e3}ms")


def fast_copy(old, new, keys_to_deepcopy: list[str] = []):
    """指定されたkeyのみdeep copyし、それ以外はshallow copyする"""
    for key, val in old.__dict__.items():
        if key in keys_to_deepcopy:
            setattr(new, key, deepcopy(val))
        else:
            setattr(new, key, recursive_copy(val))
    return new


def recursive_copy(obj):
    """オブジェクトを再帰的にコピーする"""
    if isinstance(obj, list):
        return [recursive_copy(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: recursive_copy(v) for k, v in obj.items()}
    else:
        return obj


def path(*path_parts: str):
    return resources.files("pokebot").joinpath(*path_parts)


def path_str(*path_parts: str) -> str:
    return str(resources.files("pokebot").joinpath(*path_parts))


def download(url: str, dst) -> bool:
    print(f"Downloading {url} ... ", end="")
    try:
        res = requests.get(url)
        with open(dst, 'w', encoding='utf-8') as fout:
            fout.write(res.text)
        print(f"Saved as {dst}")
        return True
    except Exception as e:
        # print(e)
        print("Failed")
        return False


def current_season() -> int:
    dt_now = datetime.now(timezone(timedelta(hours=+9), 'JST'))
    y, m, d = dt_now.year, dt_now.month, dt_now.day
    return max(12*(y-2022) + m - 11 - (d == 1), 1)


def round_half_up(v: float) -> int:
    """四捨五入"""
    return int(Decimal(str(v)).quantize(Decimal('0'), rounding=ROUND_HALF_UP))


def round_half_down(v: float) -> int:
    """五捨五超入"""
    return int(Decimal(str(v)).quantize(Decimal('0'), rounding=ROUND_HALF_DOWN))


def frac(v: float) -> float:
    """小数部分"""
    return v - int(v)


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
