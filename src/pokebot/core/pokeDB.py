from dataclasses import dataclass
import os
import json
from datetime import datetime, timedelta, timezone

from pokebot.common.enums import MoveCategory
from pokebot.common.constants import STAT_CODES
import pokebot.common.utils as ut


@dataclass
class Zukan:
    id: int
    form_id: int
    label: str
    weight: float
    types: list[str]
    abilities: list[str]
    bases: list[int]


@dataclass
class Home:
    natures: list[str]
    nature_rates: list[float]
    abilities: list[str]
    ability_rates: list[float]
    items: list[str]
    item_rates: list[float]
    terastals: list[str]
    terastal_rates: list[float]
    moves: list[str]
    move_rates: list[float]


@dataclass
class Kata:
    pokemon: str


class PokeDB:
    """ポケモンのデータ全般を保持するクラス"""
    season: int | None = None
    regulation: str | None = None

    type_file_code = {}                 # {テラスタイプ: 画像コード}
    template_file_code = {}             # {名前: テンプレート画像コード}

    zukan: dict = {}                          # 図鑑
    label_to_names: dict = {}                 # {表示名: [名前]}
    form_diff: dict = {}                      # フォルムの差分 {表示名: 'type' or 'ability'}
    jpn_to_foreign_labels: dict = {}          # {各言語の表示名: 日本語の表示名}
    foreign_to_jpn_label: dict = {}           # {日本語の表示名: [全言語の表示名]}

    abilities: list[str] = []                      # 全特性
    ability_tag: dict = {}                    # {分類タグ: [特性]}

    item_data: dict = {}                      # アイテムの基礎データ

    moves: dict = {}                          # 技の基礎データ
    move_priority: dict = {}                  # 技の優先度
    move_tag: dict = {}                       # {分類タグ: [技]}
    combo_range: dict = {}                    # 連続技の最大・最小ヒット数
    move_effect: dict = {}                    # 技の追加効果

    home: dict = {}

    kata_data: dict[str, dict] = {}                           # 型データ
    name_to_kata_name: dict[str, str] = {}              # {名前: 型の定義で使われている名前}
    name_to_kata_list: dict[str, dict] = {}              # {名前: [型]}
    item_to_kata_list: dict[str, dict] = {}              # {アイテム: [型]}
    move_to_kata_list: dict[str, dict] = {}              # {技: [型]}

    @classmethod
    def get_move_effect_value(cls, move, effect: str) -> float:
        if move.name not in cls.move_effect or \
                effect not in cls.move_effect[move.name]:
            return 0
        else:
            return cls.move_effect[move.name][effect]

    @classmethod
    def init(cls, season: int | None = None):
        cls.season = season or ut.current_season()
        cls.load_file_code()
        cls.load_zukan()
        cls.load_ability()
        cls.load_item()
        cls.load_move()
        cls.download_data()
        cls.load_home()
        cls.load_kata()
        cls.sync_zukan()

    @classmethod
    def load_file_code(cls):
        """ファイルコードの読み込み"""
        # タイプ画像コード
        with open(ut.path_str('assets', 'terastal', 'codelist.txt'), encoding='utf-8') as f:
            for line in f:
                data = line.split()
                cls.type_file_code[data[1]] = data[0]

        # テンプレート画像コード
        with open(ut.path_str('assets', 'template', 'codelist.txt'), encoding='utf-8') as f:
            for line in f:
                data = line.split()
                cls.template_file_code[data[0]] = data[1]

    @classmethod
    def load_zukan(cls):
        """図鑑の読み込み"""
        with open(ut.path_str('data', 'zukan.json'), encoding='utf-8') as f:
            for d in json.load(f).values():
                name = d['alias']
                types = [d[f'type_{i}'] for i in range(1, 3) if d[f'type_{i}']]
                abilities = [d[f'ability_{i}'] for i in range(1, 3) if d[f'ability_{i}']]
                bases = [d[s] for s in STAT_CODES[:6]]
                cls.zukan[name] = Zukan(d["id"], d["form_id"], d["name"], d["weight"],
                                        types, abilities, bases)

                cls.abilities += cls.zukan[name].abilities

                label = cls.zukan[name].label
                if label not in cls.label_to_names:
                    cls.label_to_names[label] = [name]
                elif name not in cls.label_to_names[label]:
                    # 表示名が同一、すなわちフォルム違いであれば、差分(type/ability)を記録
                    cls.label_to_names[label].append(name)
                    if cls.zukan[cls.label_to_names[label][0]].types != cls.zukan[name].types:
                        cls.form_diff[label] = "type"
                    elif cls.zukan[cls.label_to_names[label][0]].abilities != cls.zukan[name].abilities:
                        cls.form_diff[label] = "ability"

        # 重複を削除
        cls.abilities = list(set(cls.abilities))
        cls.abilities.sort()

        # 外国語名の読み込み
        with open(ut.path_str('data', 'name.json'), encoding='utf-8') as f:
            for d in json.load(f).values():
                if (label := d['JPN']) not in cls.label_to_names:
                    continue
                cls.jpn_to_foreign_labels[label] = list(d.values())
                for s in d.values():
                    cls.foreign_to_jpn_label[s] = label

    @classmethod
    def load_ability(cls):
        """技データの読み込み"""
        with open(ut.path_str('data', 'ability_tag.txt'), encoding='utf-8') as f:
            for line in f:
                data = line.split()
                cls.ability_tag[data[0]] = data[1:]

    @classmethod
    def load_item(cls):
        """アイテムデータの読み込み"""
        with open(ut.path_str('data', 'item.txt'), encoding='utf-8') as f:
            next(f)
            for line in f:
                data = line.split()
                item = data[0]

                cls.item_data[item] = {
                    'throw_power': int(data[1]),
                    'buff_type': data[2],
                    'debuff_type': data[3],
                    'power_correction': float(data[4]),
                    'consumable': int(data[5]),
                    'immediate': int(data[6]),
                    'post_hit': int(data[7]),
                }

    @classmethod
    def load_move(cls):
        """技データの読み込み"""
        with open(ut.path_str('data', 'move_tag.txt'), encoding='utf-8') as f:
            for line in f:
                data = line.split()
                cls.move_tag[data[0]] = data[1:]

        with open(ut.path_str('data', 'move_priority.txt'), encoding='utf-8') as f:
            for line in f:
                data = line.split()
                for move in data[1:]:
                    cls.move_priority[move] = int(data[0])

        with open(ut.path_str('data', 'move_effect.txt'), encoding='utf-8') as f:
            line = f.readline()
            labels = line.split()
            for line in f:
                data = line.split()
                move = data[0]
                cls.move_effect[move] = {}
                for eff, val in zip(labels[1:], data[1:]):
                    val = float(val)
                    if val.is_integer():
                        val = int(val)
                    cls.move_effect[move][eff] = val

        with open(ut.path_str('data', 'combo_move.txt'), encoding='utf-8') as f:
            for line in f:
                data = line.split()
                cls.combo_range[data[0]] = [int(data[1]), int(data[2])]

        with open(ut.path_str('data', 'attack_move.txt'), encoding='utf-8') as f:
            str_to_moveclass = {'物理': MoveCategory.PHY, '特殊': MoveCategory.SPE}

            line = f.readline()
            keys = line.split()

            for line in f:
                data = line.split()
                name = data[0]
                cls.moves[name] = {}

                for key, val in zip(keys[1:], data[1:]):
                    if key == "category":
                        val = str_to_moveclass[val]
                    elif key == "pp":
                        val = int(int(val)*1.6)
                    elif val.isdigit():
                        val = int(val)
                    cls.moves[name][key] = val

            # 威力変動技の初期化
            for move in cls.move_tag['var_power']:
                cls.moves[move]['power'] = 1

        with open(ut.path_str('data', 'status_move.txt'), encoding='utf-8') as f:
            line = f.readline()
            keys = line.split()

            for line in f:
                data = line.split()
                name = data[0]
                cls.moves[name] = {}

                for key, val in zip(keys[1:], data[1:]):
                    if key == "category":
                        val = MoveCategory.STA
                    elif key == "pp":
                        val = int(int(val)*1.6)
                    elif val.isdigit():
                        val = int(val)
                    cls.moves[name][key] = val

    @classmethod
    def download_data(cls):
        """1日1回、統計データをダウンロードする"""
        # 統計データの最終更新日を取得
        update_log = ut.path_str('data', 'last_update.txt')
        if os.path.isfile(update_log):
            with open(update_log, encoding='utf-8') as f:
                last_update = int(f.read())
        else:
            last_update = 0

        filename = ut.path_str("data", f"season{cls.season}.json")
        dt_now = datetime.now(timezone(timedelta(hours=+9), 'JST'))
        yyyymmdd = int(dt_now.strftime('%Y%m%d'))

        if not os.path.isfile(filename) or last_update < yyyymmdd:
            # HOME統計のダウンロード
            url = f"https://pbasv.cloudfree.jp/download/home/season{cls.season}.json"
            ut.download(url, filename)

            # 最終更新日を記録
            with open(update_log, 'w', encoding='utf-8') as f:
                f.write(dt_now.strftime('%Y%m%d'))

        filename = ut.path_str("data", "regulation.txt")

        if not os.path.isfile(filename) or last_update < yyyymmdd:
            # レギュレーション一覧のダウンロード
            url = "https://pbasv.cloudfree.jp/download/kata/regulation.txt"
            ut.download(url, filename)

        cls.regulation = ut.regulation(filename, cls.season)

        filename = ut.path_str("data", f"kata_reg{cls.regulation}.json")
        if not os.path.isfile(filename) or last_update < yyyymmdd:
            # 型データのダウンロード
            url = f"https://pbasv.cloudfree.jp/download/kata/kata_reg{cls.regulation}.json"
            ut.download(url, filename)

    @classmethod
    def load_home(cls):
        """HOME統計の読み込み"""
        filename = ut.path_str("data", f"season{cls.season}.json")
        with open(filename, encoding='utf-8') as f:
            for d in json.load(f).values():
                name = d['alias']
                cls.home[name] = Home(
                    d["nature"], d["nature_rate"],
                    d["ability"], d["ability_rate"],
                    d["item"], d["item_rate"],
                    d["terastal"], d["terastal_rate"],
                    d["move"], d["move_rate"]
                )
                # 補完
                if not cls.home[name].natures:
                    cls.home[name].natures = ["まじめ"]
                    cls.home[name].nature_rates = [100.]
                if not cls.home[name].abilities:
                    cls.home[name].abilities = [cls.zukan[name].abilities[0]]
                    cls.home[name].ability_rates = [100.]
                if not cls.home[name].items:
                    cls.home[name].items = [""]
                    cls.home[name].item_rates = [100.]
                if not cls.home[name].terastals:
                    cls.home[name].terastals = ["ステラ"]
                    cls.home[name].terastal_rates = [100.]
                if not cls.home[name].moves:
                    cls.home[name].moves = ["テラバースト"]
                    cls.home[name].move_rates = [100.]

    @classmethod
    def load_kata(cls):
        """型データの読み込み"""
        filename = ut.path_str("data", f"kata_reg{cls.regulation}.json")
        with open(filename, encoding='utf-8') as fin:
            d = json.load(fin)
            cls.kata_data = d['kata']
            cls.name_to_kata_name = d['valid_alias']
            cls.name_to_kata_list = d['alias2kata']
            cls.item_to_kata_list = d['item2kata']
            cls.move_to_kata_list = d['move2kata']

    @classmethod
    def sync_zukan(cls):
        """図鑑をHOMEと同期する"""
        d = {}
        for key, val in cls.zukan.items():
            if key in cls.home:
                d[key] = val
        cls.zukan = d
