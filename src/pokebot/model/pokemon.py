from __future__ import annotations

from copy import deepcopy

from pokebot.common import PokeDB
from pokebot.common.enums import Gender, Ailment
from pokebot.common.constants import STAT_CODES, NATURE_MODIFIER, EXCLUSIVE_ITEM, EXCLUSIVE_TERASTAL
import pokebot.common.utils as ut
from . import Ability, Item, Move


class Pokemon:
    def __init__(self, name: str = "ピカチュウ"):
        self._name: str = name

        self.label: str
        self.gender: Gender = Gender.NONE
        self._level: int = 50
        self._weight: float
        self._types: list[str]
        self._nature: str = "まじめ"
        self._ability: Ability = Ability()
        self._item: Item = Item()
        self._terastal: str = ""
        self._base: list[int] = [100]*6
        self._indiv: list[int] = [31]*6
        self._effort: list[int] = [0]*6
        self._stats: list[int] = [0]*6
        self.moves: list[Move] = []

        self.active: bool
        self.observed: bool
        self.is_terastallized: bool
        self._hp: int
        self._hp_ratio: float = 1.
        self.sleep_count: int
        self.ailment: Ailment
        self.speed_range: list[int]
        self.rejected_item_names: list[str]

        self.set_zukan_info()
        self.update_stats()
        self.init_kata()

        self.init_game()

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new, keys_to_deepcopy=['_ability', '_item', 'moves'])
        return new

    def __str__(self):
        sep = '\n\t'
        s = f"{self._name}{sep}"
        s += f"HP {self.hp}/{self.stats[0]} ({self.hp_ratio*100:.0f}%){sep}"
        s += f"{self._nature}{sep}"
        s += f"{self._ability}{sep}"
        s += f"{self._item}{sep}"
        s += f"{self._terastal}T{sep}"
        for st, ef in zip(self._stats, self._effort):
            s += f"{st}({ef})-" if ef else f"{st}-"
        s = s[:-1] + sep
        s += "/".join(move.name for move in self.moves)
        return s

    def init_kata(self):
        """型を初期化する"""
        if self._name in PokeDB.home:
            info = PokeDB.home[self._name]
            self.nature = info.natures[0]
            self.ability = info.abilities[0]
            self.item = info.items[0]
            self.terastal = info.terastals[0]
            self.add_moves(info.moves[:4])
        else:
            self.ability = PokeDB.zukan[self.name].abilities[0]
            self.terastal = self._types[0]

        if not self.moves:
            self.add_move('テラバースト')

    def init_game(self):
        """試合開始前の状態に初期化する"""
        self.active = False
        self.observed = False
        self.is_terastallized = False
        self.sleep_count = 0
        self.hp_ratio = 1.
        self.ailment = Ailment.NONE
        self.speed_range = [0, 999]
        self.rejected_item_names = []

        # フォルムの初期化
        match self.name:
            case 'イルカマン(マイティ)':
                self.change_form('イルカマン(ナイーブ)')
            case 'テラパゴス(ステラ)':
                self.change_form('テラパゴス(テラスタル)')

        self._ability.init_game()
        self._item.init_game()
        for move in self.moves:
            move.init_game()

        # 単一の特性・アイテムなら観測
        self._ability.observed = len(PokeDB.zukan[self._name].abilities) == 1
        self._item.observed = self._name in EXCLUSIVE_ITEM

    def bench_reset(self):
        """控えに戻した状態に初期化する"""
        # 特性の処理
        match self.ability.name:
            case 'さいせいりょく':
                self.hp = min(self.stats[0], self.hp + int(self.stats[0]/3))
            case 'しぜんかいふく':
                self.ailment = Ailment.NONE

        self.active = False
        self._ability.bench_reset()

    def dump(self) -> dict:
        d = deepcopy(vars(self))
        d['gender'] = self.gender.value
        d['_ability'] = self._ability.dump()
        d['_item'] = self._item.dump()
        d['moves'] = [move.dump() for move in self.moves]
        del d['ailment']
        return d

    def load(self, d: dict, init: bool = True):
        self.__dict__ |= d

        self.gender = Gender(d['gender'])

        self._ability = Ability()
        self._ability.load(d['_ability'])

        self._item = Item()
        self._item.load(d['_item'])

        self.moves = []
        for dmv in d['moves']:
            self.moves.append(Move())
            self.moves[-1].load(dmv)

        if init:
            self.init_game()

    def mask(self):
        """非公開情報を隠蔽(削除)する"""
        self.nature = 'まじめ'
        self._ability.mask()
        self._item.mask()
        if self.name not in EXCLUSIVE_TERASTAL:
            self.terastal = self._types[0]
        self.effort = [0]*6
        for move in self.moves:
            if not move.observed:
                self.moves.remove(move)

    def masked(self) -> Pokemon:
        """非公開情報を隠蔽したコピーを返す"""
        p = deepcopy(self)
        p.mask()
        return p

    def update_stats(self, keep_damage: bool = False):
        """ステータスを更新する。{keep_damage}=Trueなら更新前のダメージを保持し、FalseならHPを全回復する"""
        if keep_damage:
            damage = self._stats[0] - self._hp

        self._stats[0] = int((self.base[0]*2+self._indiv[0] + int(self._effort[0]/4)) * self._level/100) + self._level + 10

        for i in range(1, 6):
            self._stats[i] = int((int((self.base[i]*2 + self._indiv[i] + int(self._effort[i]/4)) * self._level/100) + 5) *
                                 NATURE_MODIFIER[self._nature][i])

        self._hp = int(self._stats[0] * self._hp_ratio)

        # HP修正
        if self._hp_ratio and self._hp == 0:
            self.hp = 1

        if keep_damage:
            self.hp = self.hp - damage

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str):
        if name not in PokeDB.zukan:
            print(f"{name} is not in PokeDB.zukan\nReplaced with ピカチュウ")
            name = 'ピカチュウ'

        self._name = name
        self.set_zukan_info()
        self.update_stats()

    def set_zukan_info(self):
        self.label = PokeDB.zukan[self._name].label
        self._weight = PokeDB.zukan[self._name].weight
        self._types = PokeDB.zukan[self._name].types.copy()
        self._base = PokeDB.zukan[self._name].bases.copy()

    def change_form(self, name: str):
        """フォルムチェンジする"""
        self._name = name
        self.set_zukan_info()
        self.update_stats(keep_damage=True)

        # 特性の変更
        if "テラパゴス" in self.name:
            self.ability = "ゼロフォーミング"

        # 技の変更
        match self._name:
            case 'ザシアン(けんのおう)':
                self.replace_move('アイアンヘッド', 'きょじゅうざん')
            case 'ザマゼンタ(たてのおう)':
                self.replace_move('アイアンヘッド', 'きょじゅうだん')

    @property
    def level(self) -> int:
        return self._level

    @level.setter
    def level(self, level: int):
        self._level = level
        self.update_stats()

    @property
    def weight(self) -> float:
        w = self._weight
        match self.ability.name:
            case 'ライトメタル':
                w = int(w*0.5*10)/10
            case 'ヘヴィメタル':
                w *= 2
        if self.item.name == 'かるいし':
            w = int(w*0.5*10)/10
        return w

    @property
    def nature(self) -> str:
        return self._nature

    @nature.setter
    def nature(self, nature: str):
        self._nature = nature
        self.update_stats()

    @property
    def ability(self) -> Ability:
        return self._ability

    @ability.setter
    def ability(self, ability: Ability | str):
        self._ability = ability if isinstance(ability, Ability) else Ability(ability)

    @property
    def item(self) -> Item:
        return self._item

    @item.setter
    def item(self, item: Item | str):
        self._item = item if isinstance(item, Item) else Item(item)

    @property
    def terastal(self) -> str | None:
        return self._terastal if self.is_terastallized else None

    @terastal.setter
    def terastal(self, type: str):
        self._terastal = type

    def terastallize(self) -> None:
        if self.is_terastallized:
            return
        self.is_terastallized = True
        if 'テラパゴス' in self.name:
            self.change_form('テラパゴス(ステラ)')
        if 'オーガポン' in self.name:
            self._ability.name = 'おもかげやどし'

    @property
    def stats(self) -> list[int]:
        return self._stats.copy()

    @stats.setter
    def stats(self, stats: list[int]):
        nc = NATURE_MODIFIER[self._nature]
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
        nc = NATURE_MODIFIER[self._nature]
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
    def base(self) -> list[int]:
        return self._base.copy()

    @base.setter
    def base(self, base: list[int]):
        self._base = base
        self.update_stats()

    @property
    def indiv(self) -> list[int]:
        return self._indiv.copy()

    @indiv.setter
    def indiv(self, indiv: list[int]):
        self._indiv = indiv
        self.update_stats()

    @property
    def effort(self) -> list[int]:
        return self._effort.copy()

    @effort.setter
    def effort(self, effort: list[int]):
        self._effort = effort
        self.update_stats()

    def set_effort(self, idx: int, value: int):
        self._effort[idx] = value
        self.update_stats()

    @property
    def hp(self) -> int:
        return self._hp

    @hp.setter
    def hp(self, hp: int):
        self._hp = hp
        self._hp_ratio = self._hp / self._stats[0]

    @property
    def hp_ratio(self) -> float:
        return self._hp_ratio

    @hp_ratio.setter
    def hp_ratio(self, hp_ratio: float):
        self._hp_ratio = hp_ratio
        self._hp = int(hp_ratio * self._stats[0])
        # HP > 0
        if hp_ratio and self._hp == 0:
            self._hp = 1

    def find_move(self, move: Move | str) -> Move | None:
        for mv in self.moves:
            if move in [mv, mv.name]:
                return mv

    def knows(self, move: Move | str) -> bool:
        return self.find_move(move) is not None

    def add_move(self, move: str | Move, pp: int = 0) -> bool:
        if isinstance(move, str):
            move = Move(move, pp=pp)
        if not self.knows(move) and move.name:
            self.moves.append(move)
            return True
        return False

    def add_moves(self, moves: list[str]):
        for move in moves:
            if len(self.moves) == 10:
                return
            self.add_move(move)

    def replace_move(self, old: str, new: str, pp: int = 0):
        for i, move in enumerate(self.moves):
            if move.name == old:
                self.moves[i] = Move(new, pp=pp)
                return

    def set_speed_limit(self, speed: int, first_act: bool):
        """先手ならSの最小値を、後手なら最大値を設定する"""
        if first_act:
            self.speed_range[0] = max(self.speed_range[0], speed)
        else:
            self.speed_range[1] = min(self.speed_range[1], speed)

    def is_sleeping(self) -> bool:
        return self.ailment == Ailment.SLP or self.ability.name == "ぜったいねむり"

    def get_negoto_moves(self) -> list[Move]:
        excluded_moves = PokeDB.tagged_moves['non_negoto'] + PokeDB.tagged_moves['charge']
        return [move for move in self.moves if move.name not in excluded_moves]

    @classmethod
    def index(cls,
              candidates: list[Pokemon],
              name: str | None = None,
              label: str | None = None) -> int | None:
        for i, p in enumerate(candidates):
            if name == p.name or label == p.label:
                return i

    @classmethod
    def find(cls,
             candidates: list[Pokemon],
             name: str | None = None,
             label: str | None = None) -> Pokemon | None:
        for p in candidates:
            if name == p.name or label == p.label:
                return p

    @classmethod
    def find_most_similar(cls, candidates: list[Pokemon], label: str) -> Pokemon | None:
        all_lang_labels = sum([PokeDB.jpn_to_foreign_labels[p.label] for p in candidates], [])
        label = ut.find_most_similar(all_lang_labels, label)
        label = PokeDB.foreign_to_jpn_label[label]
        return Pokemon.find(candidates, label=label)

    @classmethod
    def rank2str(cls, rank_list: list[int]) -> str:
        """能力ランクを 'A+1 S+1' 形式の文字列に変換"""
        s = ''
        for i, v in enumerate(rank_list):
            if rank_list[i]:
                s += f" {STAT_CODES[i]}{'+'*(v > 0)}{v}"
        return s[1:]

    @classmethod
    def calc_stats(cls,
                   name: str,
                   nature: str,
                   efforts: list[int],
                   indivs: list[int] = [31]*6) -> list[int]:
        p = Pokemon(name)
        p.nature = nature
        p.indiv = indivs
        p.effort = efforts
        p.update_stats()
        return p.stats
