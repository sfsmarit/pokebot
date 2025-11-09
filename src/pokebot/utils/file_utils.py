import requests
import jaconv
from importlib import resources
import Levenshtein
import json
import os
from datetime import datetime

from . import file_utils as fileut, str_utils as strut


LAST_UPDATE_LOG = str(fileut.resource_path("data", "last_update.json"))


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def resource_path(*path_parts: str):
    return resources.files("pokebot").joinpath(*path_parts)


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


def find_most_similar(str_list, s, ignore_dakuten=False):
    """最も似ている要素を返す"""
    if s in str_list:
        return s

    s1 = jaconv.hira2kata(s)
    if ignore_dakuten:
        s1 = strut.remove_dakuten(s1)
        str_list = list(map(strut.remove_dakuten, str_list))

    distances = [Levenshtein.distance(s1, jaconv.hira2kata(s)) for s in str_list]

    return str_list[distances.index(min(distances))]


def load_last_update(file: str) -> str:
    """JSONから最終更新日を読み込む"""
    if not os.path.exists(LAST_UPDATE_LOG):
        return ""
    with open(LAST_UPDATE_LOG, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get(file, "")


def save_last_update(file: str):
    """最終更新日をJSONに保存"""
    with open(LAST_UPDATE_LOG, "w", encoding="utf-8") as f:
        data = json.load(f)
        data[file] = today()
        json.dump(data, f, ensure_ascii=False, indent=2)


def needs_update(file: str) -> bool:
    """今日更新済みか確認"""
    last_update = load_last_update(file)
    return last_update != today()
