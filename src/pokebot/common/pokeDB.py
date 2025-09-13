from dataclasses import dataclass
import os
import json
from datetime import datetime, timedelta, timezone
import csv

from .enums import MoveCategory
from .constants import STAT_CODES
from . import utils as ut


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
class ItemData:
    """
    アイテムの基礎データ
    """
    throw_power: int
    buff_type: str
    debuff_type: str
    power_correction: float
    consumable: bool
    immediate: bool
    post_hit: bool


@dataclass
class MoveData:
    """
    技の基礎データ
    """
    type: str
    category: MoveCategory
    power: int
    hit: int
    pp: int
    protect: bool = False
    subst: bool = False
    gold: bool = False
    mirror: bool = False


@dataclass
class Home:
    """
    ポケモンHOMEの統計データ
    """
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
    """
    ポケモンの型データ
    """
    abilities: list[str]
    ability_rates: list[float]
    items: list[str]
    item_rates: list[float]
    terastals: list[str]
    terastal_rates: list[float]
    moves: list[str]
    move_rates: list[float]
    teams: list[str]
    team_rates: list[float]
    team_kata: list[str]
    team_kata_rates: list[float]


class PokeDB:
    """ポケモンのデータ全般を保持するクラス"""
    season: int
    regulation: str

    zukan: dict[str, Zukan] = {}
    label_to_names: dict[str, list[str]] = {}
    form_diff: dict[str, str] = {}
    jpn_to_foreign_labels: dict[str, list[str]] = {}
    foreign_to_jpn_label: dict[str, str] = {}

    abilities: list[str] = []
    tagged_abilities: dict[str, list[str]] = {}

    item_data: dict[str, ItemData] = {}

    move_data: dict[str, MoveData] = {}
    move_priority: dict[str, int] = {}
    move_tag: dict[str, list[str]] = {}
    combo_range: dict[str, list[int]] = {}
    move_effect: dict[str, dict] = {}

    home: dict[str, Home] = {}

    kata: dict[str, Kata] = {}
    valid_kata_name: dict[str, str] = {}
    name_to_kata_list: dict[str, dict] = {}
    item_to_kata_list: dict[str, dict] = {}
    move_to_kata_list: dict[str, dict] = {}

    @classmethod
    def items(cls) -> list[str]:
        return list(cls.item_data.keys())

    @classmethod
    def moves(cls) -> list[str]:
        return list(cls.move_data.keys())

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
        cls.load_zukan()
        cls.load_ability()
        cls.load_item()
        cls.load_move()
        cls.download_data()
        cls.load_home()
        cls.load_kata()
        cls.sync_zukan()
        print(f"Initiallized PokeDB\nseason {cls.season} / regulation {cls.regulation}")

    @classmethod
    def load_zukan(cls):
        """ポケモン図鑑の読み込み"""
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

        # 特性の追加
        cls.abilities.append("おもかげやどし")

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
        with open(ut.path_str('data', 'tagged_abilities.json'), encoding='utf-8') as f:
            cls.tagged_abilities = json.load(f)

    @classmethod
    def load_item(cls):
        """アイテムデータの読み込み"""
        with open(ut.path_str('data', 'item.txt'), encoding='utf-8') as f:
            next(f)
            for line in f:
                data = line.split()
                cls.item_data[data[0]] = ItemData(
                    throw_power=int(data[1]),
                    buff_type=data[2],
                    debuff_type=data[3],
                    power_correction=float(data[4]),
                    consumable=bool(int(data[5])),
                    immediate=bool(int(data[6])),
                    post_hit=bool(int(data[7])),
                )

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
            line = f.readline()
            for line in f:
                data = line.split()
                cls.move_data[data[0]] = MoveData(
                    type=data[1],
                    category=MoveCategory(data[2]),
                    power=int(data[3]),
                    hit=int(data[4]),
                    pp=int(int(data[5])*1.6),
                )

            # 威力変動技の初期化
            for move in cls.move_tag['var_power']:
                cls.move_data[move].power = 1

        with open(ut.path_str('data', 'status_move.txt'), encoding='utf-8') as f:
            line = f.readline()
            keys = line.split()

            for line in f:
                data = line.split()
                cls.move_data[data[0]] = MoveData(
                    type=data[1],
                    category=MoveCategory(data[2]),
                    power=int(data[3]),
                    hit=int(data[4]),
                    pp=int(int(data[5])*1.6),
                    protect=bool(int(data[6])),
                    subst=bool(int(data[7])),
                    gold=bool(int(data[8])),
                    mirror=bool(int(data[9])),
                )

    @classmethod
    def download_data(cls):
        """統計データをダウンロードする"""
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

        # レギュレーションの一覧が記されたファイルをダウンロード
        filename = ut.path_str("data", "regulation.csv")
        if not os.path.isfile(filename) or last_update < yyyymmdd:
            url = "https://pbasv.cloudfree.jp/download/kata/regulation.csv"
            ut.download(url, filename)

        # レギュレーション一覧を取得
        regulations = ['']
        with open(filename, encoding='utf-8', newline='\r\n') as f:
            reader = csv.reader(f)
            for row in reader:
                regulations.append(row[1])

        # 現在のレギュレーションを取得
        if cls.season <= len(regulations) - 1:
            cls.regulation = regulations[cls.season]
        else:
            cls.regulation = regulations[-1]

        # デイリーで、レギュレーションに対応した型データをダウンロード
        filename = ut.path_str("data", f"kata_reg{cls.regulation}.json")
        if not os.path.isfile(filename) or last_update < yyyymmdd:
            url = f"https://pbasv.cloudfree.jp/download/kata/kata_reg{cls.regulation}.json"
            ut.download(url, filename)

    @classmethod
    def load_home(cls):
        """ポケモンHOME統計データの読み込み"""
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
            kata_data = d['kata']
            cls.valid_kata_name = d['valid_alias']
            cls.name_to_kata_list = d['alias2kata']
            cls.item_to_kata_list = d['item2kata']
            cls.move_to_kata_list = d['move2kata']

        for kata, data in kata_data.items():
            cls.kata[kata] = Kata(
                list(data['ability'].keys()), list(data['ability'].values()),
                list(data['item'].keys()), list(data['item'].values()),
                list(data['terastal'].keys()), list(data['terastal'].values()),
                list(data['move'].keys()), list(data['move'].values()),
                list(data['team'].keys()), list(data['team'].values()),
                list(data['team_kata'].keys()), list(data['team_kata'].values()),
            )

    @classmethod
    def sync_zukan(cls):
        """図鑑をHOMEと同期する"""
        d = {}
        for key, val in cls.zukan.items():
            if key in cls.home:
                d[key] = val
        cls.zukan = d
