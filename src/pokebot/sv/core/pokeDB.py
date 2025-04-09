import os
import json
from datetime import datetime, timedelta, timezone

from pokebot.sv.constants import STAT_CODES
import pokebot.sv.utils as ut


class PokeDB:
    """ポケモンのデータ全般を保持するクラス"""
    season = None                       # ランクマッチ シーズン
    regulation = None                   # ランクマッチ レギュレーション

    type_file_code = {}                 # {テラスタイプ: 画像コード}
    template_file_code = {}             # {名前: テンプレート画像コード}

    zukan = {}                          # 図鑑
    label_to_kata_names = {}            # {表示名: [名前]}
    form_diff = {}                      # フォルムの差分 {表示名: 'type' or 'ability'}
    jpn_to_foreign_labels = {}          # {各言語の表示名: 日本語の表示名}
    foreign_to_jpn_label = {}           # {日本語の表示名: [全言語の表示名]}

    abilities = []                      # 全特性
    category_to_abilities = {}          # {分類: [特性]}

    item_data = {}                      # アイテムの基礎データ

    moves = {}                          # 技の基礎データ
    move_to_priority = {}               # 技の優先度
    category_to_moves = {}              # 技の分類
    move_to_effect_value = {}           # 反動や回復量など
    move_to_combo_range = {}            # 連続技の最大・最小ヒット数
    move_to_effect = {}                 # 技の追加効果

    home = {}                           # ポケモンHOMEの統計データ

    name_to_kata_name = {}              # {名前: 型集計で使われる名前}
    name_to_kata_list = {}              # {名前: [型]}
    kata = {}                           # 型データ
    item_to_kata_list = {}              # {アイテム: [型]}
    move_to_kata_list = {}              # {技: [型]}

    def init(season: int = None):
        PokeDB.season = season or ut.current_season()
        PokeDB.load_file_code()
        PokeDB.load_zukan()
        PokeDB.load_ability()
        PokeDB.load_item()
        PokeDB.load_move()
        PokeDB.load_zukan()
        PokeDB.download_data()
        PokeDB.load_home()
        PokeDB.load_kata()
        PokeDB.sync_zukan()

    def load_file_code():
        """ファイルコードの読み込み"""
        # タイプ画像コード
        with open(ut.path_str('assets', 'terastal', 'codelist.txt'), encoding='utf-8') as f:
            for line in f:
                data = line.split()
                PokeDB.type_file_code[data[1]] = data[0]

        # テンプレート画像コード
        with open(ut.path_str('assets', 'template', 'codelist.txt'), encoding='utf-8') as f:
            for line in f:
                data = line.split()
                PokeDB.template_file_code[data[0]] = data[1]

    def load_zukan():
        """図鑑の読み込み"""
        with open(ut.path_str('data', 'zukan.json'), encoding='utf-8') as f:
            for d in json.load(f).values():
                name = d['alias']
                PokeDB.zukan[name] = {}
                PokeDB.zukan[name]['id'] = d['id']
                PokeDB.zukan[name]['form_id'] = d['form_id']
                PokeDB.zukan[name]['label'] = d['name']
                PokeDB.zukan[name]['weight'] = d['weight']
                PokeDB.zukan[name]['type'] = [
                    d[f'type_{i}'] for i in range(1, 3) if d[f'type_{i}']
                ]
                PokeDB.zukan[name]['ability'] = [
                    d[f'ability_{i}'] for i in range(1, 3) if d[f'ability_{i}']
                ]
                PokeDB.zukan[name]['base'] = [d[s] for s in STAT_CODES[:6]]

                PokeDB.abilities += PokeDB.zukan[name]['ability']

                if (label := d['name']) not in PokeDB.label_to_kata_names:
                    PokeDB.label_to_kata_names[label] = [name]

                elif name not in PokeDB.label_to_kata_names[label]:
                    # 表示名が同一、すなわちフォルム違いであれば、差分(タイプまたは特性)を記録
                    PokeDB.label_to_kata_names[label].append(name)
                    for key in ['type', 'ability']:
                        if PokeDB.zukan[PokeDB.label_to_kata_names[label][0]][key] != PokeDB.zukan[name][key]:
                            PokeDB.form_diff[label] = key
                            break

        # 重複を削除
        PokeDB.abilities = list(set(PokeDB.abilities))

        # 外国語名の読み込み
        with open(ut.path_str('data', 'name.json'), encoding='utf-8') as f:
            for d in json.load(f).values():
                if (label := d['JPN']) not in PokeDB.label_to_kata_names:
                    continue
                PokeDB.jpn_to_foreign_labels[label] = list(d.values())
                for s in d.values():
                    PokeDB.foreign_to_jpn_label[s] = label

    def load_ability():
        """技データの読み込み"""
        with open(ut.path_str('data', 'ability_category.txt'), encoding='utf-8') as f:
            for line in f:
                data = line.split()
                PokeDB.category_to_abilities[data[0]] = data[1:]

    def load_item():
        """アイテムデータの読み込み"""
        with open(ut.path_str('data', 'item.txt'), encoding='utf-8') as f:
            next(f)
            for line in f:
                data = line.split()
                item = data[0]

                # なげつける威力
                PokeDB.item_data[item] = {
                    'throw_power': int(data[1]),
                    'buff_type': data[2],
                    'debuff_type': data[3],
                    'power_correction': float(data[4]),
                    'consumable': bool(data[5]),
                    'immediate': bool(data[6])
                }

    def load_move():
        """技データの読み込み"""
        with open(ut.path_str('data', 'move_category.txt'), encoding='utf-8') as f:
            for line in f:
                data = line.split()
                PokeDB.category_to_moves[data[0]] = data[1:]

        with open(ut.path_str('data', 'move_priority.txt'), encoding='utf-8') as f:
            for line in f:
                data = line.split()
                for s in data[1:]:
                    PokeDB.move_to_priority[s] = int(data[0])

        with open(ut.path_str('data', 'move_effect.txt'), encoding='utf-8') as f:
            next(f)
            for line in f:
                data = line.split()
                move = data[0]
                effect = {}
                effect['target'] = int(data[1])
                effect['prob'] = float(data[2])
                effect['rank'] = [0] + list(map(int, data[3:10]))
                effect['ailment'] = list(map(int, data[10:15]))
                effect['confusion'] = int(data[15])
                effect['flinch'] = float(data[16])
                effect['drain'] = float(data[17])
                effect['recoil'] = float(data[18])
                effect['mis_recoil'] = float(data[19])
                effect['cost'] = float(data[20])
                PokeDB.move_to_effect[move] = effect

        with open(ut.path_str('data', 'combo_move.txt'), encoding='utf-8') as f:
            for line in f:
                data = line.split()
                PokeDB.move_to_combo_range[data[0]] = [int(data[1]), int(data[2])]

        with open(ut.path_str('data', 'move.txt'), encoding='utf-8') as f:
            eng = {'物理': 'phy', '特殊': 'spe'}
            next(f)
            for line in f:
                data = line.split()
                if '変化' in data[2]:
                    data[2] = 'sta' + format(int(data[2][2:]), '04b')
                else:
                    data[2] = eng[data[2]]
                PokeDB.moves[data[0]] = {
                    'type': data[1],
                    'class': data[2],
                    'power': int(data[3]),
                    'hit': int(data[4]),
                    'pp': int(int(data[5])*1.6)
                }

            # 威力変動技の威力を1に初期化
            for s in PokeDB.category_to_moves['var_power']:
                PokeDB.moves[s]['power'] = 1

    def download_data():
        """1日1回、統計データをダウンロードする"""
        # 統計データの最終更新日を取得
        update_log = ut.path_str('data', 'last_update.txt')
        if os.path.isfile(update_log):
            with open(update_log, encoding='utf-8') as f:
                last_update = int(f.read())
        else:
            last_update = 0

        filename = ut.path_str("data", f"season{PokeDB.season}.json")
        dt_now = datetime.now(timezone(timedelta(hours=+9), 'JST'))
        yyyymmdd = int(dt_now.strftime('%Y%m%d'))

        if not os.path.isfile(filename) or last_update < yyyymmdd:
            # HOME統計のダウンロード
            url = f"https://pbasv.cloudfree.jp/download/home/season{PokeDB.season}.json"
            ut.download(url, filename)

            # 最終更新日を記録
            with open(update_log, 'w', encoding='utf-8') as f:
                f.write(dt_now.strftime('%Y%m%d'))

        filename = ut.path_str("data", "regulation.txt")

        if not os.path.isfile(filename) or last_update < yyyymmdd:
            # レギュレーション一覧のダウンロード
            url = "https://pbasv.cloudfree.jp/download/kata/regulation.txt"
            ut.download(url, filename)

        PokeDB.regulation = ut.regulation(filename, PokeDB.season)

        filename = ut.path_str("data", f"kata_reg{PokeDB.regulation}.json")
        if not os.path.isfile(filename) or last_update < yyyymmdd:
            # 型データのダウンロード
            url = f"https://pbasv.cloudfree.jp/download/kata/kata_reg{PokeDB.regulation}.json"
            ut.download(url, filename)

    def load_home():
        """HOME統計の読み込み"""
        filename = ut.path_str("data", f"season{PokeDB.season}.json")
        with open(filename, encoding='utf-8') as f:
            for d in json.load(f).values():
                name = d['alias']

                PokeDB.home[name] = {}
                for key in list(d.keys())[-10:]:
                    PokeDB.home[name][key] = d[key]

                # データの補完
                if not PokeDB.home[name]['nature']:
                    PokeDB.home[name]['nature'] = ['まじめ']
                    PokeDB.home[name]['nature_rate'] = [100]
                if not PokeDB.home[name]['ability']:
                    PokeDB.home[name]['ability'] = [
                        PokeDB.zukan[name]['ability'][0]]
                    PokeDB.home[name]['ability_rate'] = [100]
                if not PokeDB.home[name]['item']:
                    PokeDB.home[name]['item'] = ['']
                    PokeDB.home[name]['item_rate'] = [100]
                if not PokeDB.home[name]['terastal']:
                    PokeDB.home[name]['terastal'] = [
                        PokeDB.zukan[name]['type'][0]]
                    PokeDB.home[name]['terastal_rate'] = [100]

    def load_kata():
        """型データの読み込み"""
        filename = ut.path_str("data", f"kata_reg{PokeDB.regulation}.json")
        with open(filename, encoding='utf-8') as fin:
            d = json.load(fin)
            PokeDB.valid_name_for_kata = d['valid_alias']
            PokeDB.name_to_kata_list = d['alias2kata']
            PokeDB.kata = d['kata']
            PokeDB.item_to_kata_list = d['item2kata']
            PokeDB.move_to_kata_list = d['move2kata']

    def sync_zukan():
        """図鑑をHOMEと同期する"""
        d = {}
        for key, val in PokeDB.zukan.items():
            if key in PokeDB.home:
                d[key] = val
        PokeDB.zukan = d


if __name__ == '__main__':
    pass
