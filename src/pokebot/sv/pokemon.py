from __future__ import annotations

from copy import deepcopy
import warnings

from pokebot.sv.pokeDB import PokeDB
from pokebot.sv.ability import Ability
from pokebot.sv.item import Item
from pokebot.sv.move import Move
import pokebot.sv.utils as ut

from pokebot.sv.constants import Gender, BoostSource, \
    NATURE_MODIFIERS, EXCLUSIVE_ITEMS, EXCLUSIVE_TERASTALS


class Pokemon:
    def __init__(self, name: str = 'ピカチュウ'):
        self.gender = Gender.NONE           # 性別
        self._level = 50                    # レベル
        self._nature = 'まじめ'             # 性格
        self._stats = [0]*6                 # ステータス
        self._indiv = [31]*6                # 個体値
        self._effort = [0]*6                # 努力値
        self.item = Item()                  # アイテム
        self.moves = []                     # [技]
        self._hp_ratio = 1.0                # HP割合

        # 名前 (setterで図鑑情報とステータスも設定される)
        self.name = name

        self.ability = Ability(PokeDB.zukan[self.name]['ability'][0])  # 特性
        self.terastal = self._types[0]         # テラスタイプ

        self.game_reset()

        # 型の初期化
        if self._name in PokeDB.home:
            self.nature = PokeDB.home[self.name]['nature'][0]
            self.ability = Ability(PokeDB.home[self.name]['ability'][0])
            self.item = Item(PokeDB.home[self.name]['item'][0])
            self.terastal = PokeDB.home[self.name]['terastal'][0]
            self.add_moves(PokeDB.home[self.name]['move'][:4])
        else:
            self.add_move('テラバースト')

    def game_reset(self):
        """試合開始前の状態に初期化"""
        self.observed = False                   # ポケモンが観測されたらTrue
        self._hp = self._stats[0]               # 残りHP
        self._hp_ratio = 1                      # 残りHP割合
        self.ailment = None                     # 状態異常
        self._is_terastallized = False          # テラスタルしたらTrue
        self.sleep_turn = 0                    # ねむり残りターン
        self.rejected_item_names = []           # 公開情報から棄却されるアイテム. list[str]
        self.speed_range = [0, 999]             # 素早さ推定範囲

        self.bench_reset()

        # フォルムの初期化
        match self.name:
            case 'イルカマン(マイティ)':
                self.change_form('イルカマン(ナイーブ)')
            case 'テラパゴス(ステラ)':
                self.change_form('テラパゴス(テラスタル)')

        # 特性の初期化。単一特性なら観測
        self.ability.game_reset()
        self.ability.observed = len(PokeDB.zukan[self._name]['ability']) == 1

        # アイテムの初期化。単一特性なら観測
        self.item.game_reset()
        self.item.observed = self._name in EXCLUSIVE_ITEMS

        # 技の初期化
        for move in self.moves:
            move.game_reset()

    def bench_reset(self):
        """控えに戻した状態にする"""
        self.no_act()

        self.rank = [0]*8                   # 能力ランク [H,A,B,C,D,S,命中,回避]
        self.expended_moves = []            # 選択した技 (=PPを消費した技) の履歴
        self.lost_types = []                # [失ったタイプ]
        self.added_types = []               # [追加されたタイプ]
        self.sub_hp = 0                     # みがわりの残りHP
        self.boosted_idx = None             # 強化された能力index
        self._boost_source = None              # 能力上昇の原因
        self.active_turn = 0                # 行動したターン数
        self.unresponsive_turn = 0          # 命令できない状態の残りターン数
        self.hits_taken = 0                 # 被弾回数
        self.choice_locked = False          # こだわり状態ならTrue
        self.lockon = False                 # ロックオンしている状態ならTrue
        self.rank_dropped = False           # ランク下降していればTrue
        self.berserk_triggered = False      # ぎゃくじょうの発動条件を満たしていればTrue

        # 特性の処理
        match self.ability.name:
            case 'さいせいりょく':
                self.hp = min(self._stats[0], self.hp + int(self._stats[0]/3))
            case 'しぜんかいふく':
                self.ailment = None

        self.condition = {
            'confusion': 0,                 # こんらん 残りターン
            'critical': 0,                  # 急所ランク上昇
            'aquaring': 0,                  # アクアリング
            'healblock': 0,                 # かいふくふうじ 残りターン
            'magnetrise': 0,                # でんじふゆう 残りターン
            'noroi': 0,                     # のろい
            'horobi': 0,                    # ほろびのうたカウント
            'yadorigi': 0,                  # やどりぎのタネ

            # 以上がバトンタッチ対象

            'ame_mamire': 0,                # あめまみれ 残りターン
            'encore': 0,                    # アンコール 残りターン
            'anti_air': 0,                  # うちおとす
            'kanashibari': 0,               # かなしばり 残りターン
            'shiozuke': 0,                  # しおづけ
            'jigokuzuki': 0,                # じごくづき 残りターン
            'charge': 0,                    # じゅうでん
            'stock': 0,                     # たくわえるカウント
            'chohatsu': 0,                  # ちょうはつ 残りターン
            'switchblock': 0,               # にげられない
            'nemuke': 0,                    # ねむけ 残りターン
            'neoharu': 0,                   # ねをはる
            'michizure': 0,                 # みちづれ
            'meromero': 0,                  # メロメロ
            'badpoison': 0,                 # もうどくカウント
            'bind': 0,                      # バインド (残りターン)+0.1*(ダメージ割合)
        }

        # 特性の初期化
        self.ability.bench_reset()

    def no_act(self):
        """そのターンに行動できなかったときの処理"""
        self.executed_move = None           # 最後に出た技
        self.hidden = False                 # 技で隠れている状態ならTrue

    def __str__(self):
        sep = '\n\t'
        s = f"{self._name}{sep}"
        s += f"HP {self.hp}/{self.stats[0]} ({self.hp_ratio*100:.1f}%){sep}"
        s += f"{self._nature}{sep}"
        s += f"{self.ability}{sep}"
        s += f"{self.item}{sep}"
        s += f"{self.terastal}T{sep}"
        for st, ef in zip(self._stats, self._effort):
            s += f"{st}({ef})-" if ef else f"{st}-"
        s = s[:-1] + sep
        s += f"{'/'.join(move.name for move in self.moves)}"
        return s

    def dump(self) -> dict:
        d = deepcopy(vars(self))
        d['gender'] = self.gender.value
        d['ability'] = self.ability.dump()
        d['item'] = self.item.dump()
        d['moves'] = [move.dump() for move in self.moves]
        return d

    def load(self, d: dict):
        self.__dict__ |= d

        self.gender = Gender(d['gender'])

        self.ability = Ability()
        self.ability.load(d['ability'])

        self.item = Item()
        self.item.load(d['item'])

        self.moves = []
        for dmv in d['moves']:
            self.moves.append(Move())
            self.moves[-1].load(dmv)

    def mask(self):
        """非公開情報を隠蔽"""
        # 性格
        self.nature = 'まじめ'

        # 特性
        self.ability.mask()

        # アイテム
        self.item.mask()

        # テラスタイプ
        if self.name not in PokeDB.unique_terastal_pokemons:
            self.terastal = self._types[0]

        # 努力値
        self.effort = [0]*6

        # 技
        for move in self.moves:
            if not move.observed:
                self.moves.remove(move)

    def masked(self) -> Pokemon:
        """非公開情報を隠蔽するしたコピーを返す"""
        p = deepcopy(self)
        p.mask()
        return p

    def update_stats(self, keep_damage: bool = False):
        """ステータスを更新する
        {keep_damage}=Trueなら更新前のダメージを保持し、FalseならHPを全回復する"""
        nm = NATURE_MODIFIERS[self._nature]
        damage = self._stats[0] - self._hp if keep_damage else 0

        self._stats[0] = int((self.base[0]*2+self._indiv[0] +
                              int(self._effort[0]/4))*self._level/100)+self._level+10

        for i in range(1, 6):
            self._stats[i] = int((int((self.base[i]*2 + self._indiv[i] +
                                       int(self._effort[i]/4))*self._level/100)+5)*nm[i])

        self._hp = int(self._stats[0] * self._hp_ratio)

        # HP > 0
        if self._hp_ratio and self._hp == 0:
            self._hp = 1

        self.hp = self.hp - damage

    def index(pokemon_list: list[Pokemon], name: str = None, label: str = None) -> int:
        """条件に合致したポケモンの番号を返す"""
        for i, p in enumerate(pokemon_list):
            if name == p.name or label == p.label:
                return i

    def find(pokemon_list: list[Pokemon], name: str = None, label: str = None) -> Pokemon:
        """条件に合致したポケモンを返す"""
        for p in pokemon_list:
            if name == p.name or label == p.label:
                return p

    def find_most_similar(pokemon_list: list[Pokemon], label: str) -> Pokemon:
        """表示名(外国語でも可)が最も類似したポケモンを返す"""
        candidates = sum([PokeDB.jpn2foreign_labels[p.label]
                         for p in pokemon_list], [])
        s = ut.find_most_similar(candidates, label)
        s = PokeDB.foreign2jpn_label[s]  # 和訳
        return Pokemon.find(pokemon_list, label=s)

    def rank2str(rank_list: list[int]) -> str:
        """能力ランクを 'A+1 S+1' 形式の文字列に変換"""
        s = ''
        for i, v in enumerate(rank_list):
            if rank_list[i]:
                s += f" {PokeDB.stats_label[i]}{'+'*(v > 0)}{v}"
        return s[1:]

    def calculate_stats(name: str, nature: str, efforts: list[int], indivs: list[int] = [31]*6) -> list[int]:
        """ステータスを更新"""
        p = Pokemon(name)
        p.nature = nature
        p.indiv = indivs
        p.effort = efforts
        p.update_stats()
        return p.stats

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name: str):
        if name not in PokeDB.zukan:
            warnings.warn(f'{name} is not in PokeDB.zukan -> ピカチュウ')
            name = 'ピカチュウ'

        self._name = name
        self.set_zukan_data()
        self.update_stats()

    def set_zukan_data(self):
        self.label = PokeDB.zukan[self._name]['label']
        self._types = PokeDB.zukan[self._name]['type'].copy()
        self._base = PokeDB.zukan[self._name]['base'].copy()
        self._weight = PokeDB.zukan[self._name]['weight']

    def change_form(self, name: str):
        """フォルムを変更する"""
        if name not in PokeDB.zukan:
            warnings.warn(f'{name} is not in PokeDB.zukan')
            return

        self._name = name
        self.set_zukan_data()
        self.update_stats(keep_damage=True)  # ダメージを残す

        # 技の書き換え
        match self._name:
            case 'ザシアン(けんのおう)':
                self.replace_move('アイアンヘッド', 'きょじゅうざん')
            case 'ザマゼンタ(たてのおう)':
                self.replace_move('アイアンヘッド', 'きょじゅうだん')

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level: int):
        self._level = level
        self.update_stats()

    @property
    def weight(self):
        w = self._weight
        match self.ability.name:
            case 'ライトメタル':
                w = int(w*0.5*10)/10
            case 'ヘヴィメタル':
                w *= 2
        if self.item == 'かるいし':
            w = int(w*0.5*10)/10
        return w

    @property
    def nature(self):
        return self._nature

    @nature.setter
    def nature(self, nature: str):
        self._nature = nature
        self.update_stats()

    @property
    def org_types(self):
        return self._types.copy()

    @property
    def types(self):
        if self.terastal:
            if self.terastal == 'ステラ':
                return self._types.copy()
            else:
                return [self.terastal]
        else:
            if self._name == 'アルセウス':
                return [PokeDB.plate2type[self.item.name] if
                        self.item.name in PokeDB.plate2type else 'ノーマル']
            else:
                return self.added_types + \
                    [t for t in self._types if t not in self.lost_types + self.added_types]

    @property
    def terastal(self):
        return self._terastal if self._is_terastallized else None

    @terastal.setter
    def terastal(self, terastal: str | bool):
        """{terastal}の型がstrならテラスタイプを設定し、boolならテラスタルを発動する"""
        if isinstance(terastal, str):
            self._terastal = terastal
        elif isinstance(terastal, bool) and terastal:
            self._is_terastallized = True
            if 'テラパゴス' in self.name:
                self.change_form('テラパゴス(ステラ)')
            if 'オーガポン' in self.name:
                self.ability.name = 'おもかげやどし'

    @property
    def stats(self):
        return self._stats.copy()

    @stats.setter
    def stats(self, stats: list[int]):
        nc = NATURE_MODIFIERS[self._nature]
        efforts_50 = [0] + [4+8*i for i in range(32)]

        for i in range(6):
            for eff in efforts_50:
                if i == 0:
                    v = int((self._base[0]*2+self._indiv[0]+int(eff/4))*self._level/100)+self._level+10
                else:
                    v = int((int((self._base[i]*2+self._indiv[i]+int(eff/4))*self._level/100)+5)*nc[i])
                if v == stats[i]:
                    self._effort[i] = eff
                    self._stats[i] = v
                    break

    def set_stats(self, idx: int, value: int) -> bool:
        nc = NATURE_MODIFIERS[self._nature]
        efforts_50 = [0] + [4+8*i for i in range(32)]

        for eff in efforts_50:
            if idx == 0:
                v = int((self._base[0]*2+self._indiv[0]+int(eff/4))*self._level/100)+self._level+10
            else:
                v = int((int((self._base[idx]*2+self._indiv[idx]+int(eff/4))*self._level/100)+5)*nc[idx])
            if v == value:
                self._effort[idx] = eff
                self._stats[idx] = v
                return True

        return False

    @property
    def base(self):
        return self._base.copy()

    @base.setter
    def base(self, base: list[int]):
        self._base = base
        self.update_stats()

    @property
    def indiv(self):
        return self._indiv.copy()

    @indiv.setter
    def indiv(self, indiv: list[int]):
        self._indiv = indiv
        self.update_stats()

    @property
    def effort(self):
        return self._effort.copy()

    @effort.setter
    def effort(self, effort: list[int]):
        self._effort = effort
        self.update_stats()

    def set_effort(self, idx: int, value: list[int]):
        self._effort[idx] = value
        self.update_stats()

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, hp: int):
        self._hp = hp
        self._hp_ratio = self._hp / self._stats[0]

    @property
    def hp_ratio(self):
        return self._hp_ratio

    @hp_ratio.setter
    def hp_ratio(self, hp_ratio: float):
        self._hp_ratio = hp_ratio
        self._hp = int(hp_ratio * self._stats[0])
        # HP > 0
        if hp_ratio and self._hp == 0:
            self._hp = 1

    @property
    def boost_source(self):
        return self._boost_source

    @boost_source.setter
    def boost_source(self, boost_source: BoostSource):
        self._boost_source = boost_source
        if boost_source != BoostSource.NONE:
            a = [0] + [v*self.rank_correction(i) for i, v in enumerate(self._stats[1:])]
            self.boosted_idx = a.index(max(a))
        else:
            self.boosted_idx = None

    def find_move(self, move: Move | str) -> Move:
        for mv in self.moves:
            if mv == move:
                return mv

    def knows(self, move: Move | str) -> bool:
        """技を覚えていたらTrue"""
        return self.find_move(move) is not None

    def add_move(self, move: str, pp: int = None):
        """技を追加"""
        if len(self.moves) == 10:
            warnings.warn("Numbe of moves must be <= 10")
        elif self.knows(move):
            warnings.warn(f'Already knows {move}')
        else:
            if (obj := Move(move, pp=pp)):
                self.moves.append(obj)

    def add_moves(self, moves: list[str]):
        """技を複数追加"""
        for move in moves:
            if len(self.moves) == 10:
                return
            self.add_move(move)

    def replace_move(self, old: str, new: str, pp: int = None):
        """技を置換"""
        for i, move in enumerate(self.moves):
            if move == old:
                self.moves[i] = Move(new, pp=pp)
                return

    def eff_move_class(self, move: Move) -> str:
        """実効的な技の分類"""
        if move.name in ['テラバースト', 'テラクラスター'] and self.terastal:
            effA = self._stats[1]*self.rank_correction(1)
            effC = self._stats[3]*self.rank_correction(3)
            return 'phy' if effA >= effC else 'spe'
        else:
            return move.cls

    def rank_correction(self, idx: int) -> float:
        """ランク補正値. idx: 0~7 (H,A,B,C,D,S,命中,回避)"""
        if self.rank[idx] >= 0:
            return (self.rank[idx]+2)/2
        else:
            return 2/(2-self.rank[idx])

    def is_ability_protected(self) -> bool:
        """特性が上書きされない状態ならTrue"""
        return self.ability.protected or self.item == 'とくせいガード'

    def is_contact_move(self, move: Move) -> bool:
        """接触攻撃ならTrue"""
        return move.name in PokeDB.move_category['contact'] and \
            self.ability != 'えんかく' and self.item != 'ぼうごパッド' and \
            not (move.name in PokeDB.move_category['punch']
                 and self.item == 'パンチグローブ')

    def is_item_removable(self):
        """アイテムを奪われる状態ならTrue"""
        if self._name in PokeDB.unique_item_pokemons or \
            self.ability == 'ねんちゃく' or \
            self.item == 'ブーストエナジー' or \
            (self._name == 'アルセウス' and self.item.name[-4:] == 'プレート') or \
                (self._name == 'ゲノセクト' and self.item.name[-4:] == 'カセット'):
            return False
        return True

    def fruit_recovery(self, hp_dict: dict) -> dict:
        """木の実で回復した後のHP辞書を返す"""
        result = {}

        for hp in hp_dict:
            if hp == '0' or hp[-2:] == '.0':
                ut.push(result, hp, hp_dict[hp])

            elif self.item.name in ['オレンのみ', 'オボンのみ']:
                if float(hp) <= 0.5*self._stats[0]:
                    recovery = int(
                        self._stats[0]/4) if self.item == 'オボンのみ' else 10
                    key = str(min(self.hp, int(float(hp)) + recovery)) + '.0'
                    ut.push(result, key, hp_dict[hp])
                else:
                    ut.push(result, hp, hp_dict[hp])

            elif self.item.name in ['フィラのみ', 'ウイのみ', 'マゴのみ', 'バンジのみ', 'イアのみ']:
                if float(hp)/self._stats[0] <= (0.5 if self.ability == 'くいしんぼう' else 0.25):
                    key = str(int(float(hp)) + int(self._stats[0]/3)) + '.0'
                    ut.push(result, key, hp_dict[hp])
                else:
                    ut.push(result, hp, hp_dict[hp])

        return result

    def set_speed_limit(self, speed: int, first_act: bool):
        """先手ならSの最小値を、後手なら最大値を設定する"""
        if first_act:
            self.speed_range[0] = max(self.speed_range[0], speed)
        else:
            self.speed_range[1] = min(self.speed_range[1], speed)
        # print(f"{self.name} S({self.stats[5]}) 推定{self.speed_range[0]}~{self.speed_range[1]}")

    def negoto_moves(self):
        """ねごとで選ばれる技の一覧を返す"""
        excluded = [''] + PokeDB.move_category['non_negoto'] + PokeDB.move_category['charge']
        return [move for move in self.moves if move.name not in excluded]


if __name__ == '__main__':
    Pokemon()
