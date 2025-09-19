from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from battle import Battle
    from pokebot.player import Player

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Ailment, Condition, BoostSource, \
    MoveCategory, GlobalField
from pokebot.common.constants import EXCLUSIVE_ITEM, PLATE_TYPE
import pokebot.common.utils as ut
from pokebot.common import PokeDB
from pokebot.model import Pokemon, Ability, Move
from pokebot.logger import TurnLog

from .pokemon_methods.activate_ability import _activate_ability
from .pokemon_methods.activate_item import _activate_item
from .pokemon_methods.activate_move_effect import _activate_move_effect
from .pokemon_methods.apply_move_recoil import _apply_move_recoil
from .pokemon_methods.process_tagged_move import _process_tagged_move
from .pokemon_methods.ailment import _set_ailment
from .pokemon_methods.condition import _set_condition, _add_condition_count
from .pokemon_methods.hp import _add_hp
from .pokemon_methods.rank import _add_rank
from .pokemon_methods.can_choose_move import _can_choose_move
from .pokemon_methods.speed import _effective_speed


class ActivePokemonManager:
    """
    場に出ているポケモンの状態を管理するクラス
    """

    def __init__(self, battle: Battle, idx: PlayerIndex | int):
        self.battle: Battle = battle
        self.idx: PlayerIndex | int = idx

        self.consumed_stellar_types: list[str]

        self.choice_locked: bool
        self.hidden: bool
        self.lockon: bool
        self.rank_dropped: bool
        self.berserk_triggered: bool
        self.active_turn: int
        self.forced_turn: int
        self.sub_hp: int
        self.bind_damage_denom: int
        self.hits_taken: int
        self.boosted_idx: int | None
        self._boost_source: BoostSource
        self.rank: list[int]
        self.added_types: list[str]
        self.lost_types: list[str]
        self.count: dict = {}
        self.executed_move: Move
        self.expended_moves: list[Move]

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new)
        return new

    def dump(self) -> dict:
        d = ut.recursive_copy(vars(self))
        del d['battle']  # type: ignore
        return d  # type: ignore

    def load(self, d: dict):
        self.__dict__ |= d

    def init_game(self):
        """試合開始前の状態に初期化する"""
        self.consumed_stellar_types = []
        self.no_act()
        self.bench_reset()

    def bench_reset(self):
        """控えに戻した状態に初期化する"""
        self.choice_locked = False
        self.hidden = False
        self.lockon = False
        self.rank_dropped = False
        self.berserk_triggered = False
        self.active_turn = 0
        self.forced_turn = 0
        self.sub_hp = 0
        self.bind_damage_denom = 8
        self.hits_taken = 0
        self.boosted_idx = None
        self._boost_source = BoostSource.NONE
        self.reset_rank()
        self.added_types = []
        self.lost_types = []
        for cond in Condition:
            self.count[cond] = 0
        self.executed_move = Move()
        self.expended_moves = []

        if self.pokemon:
            self.pokemon.bench_reset()

    def no_act(self):
        """そのターンに行動できなかったときの処理"""
        self.hidden = False
        self.forced_turn = 0

    def reset_rank(self):
        self.rank = [0] * 8

    @property
    def player(self) -> Player:
        return self.battle.players[self.idx]

    @property
    def pokemon(self) -> Pokemon:
        return self.battle.pokemons[self.idx]

    @property
    def opponent(self) -> Pokemon:  # type: ignore
        return self.battle.pokemons[not self.idx]

    @property
    def types(self) -> list[str]:
        """場のポケモンのタイプを返す"""
        if self.pokemon.terastal:
            if self.pokemon.terastal == 'ステラ':
                return self.pokemon._types.copy()
            else:
                return [self.pokemon.terastal]
        else:
            if self.pokemon.name == 'アルセウス':
                return [PLATE_TYPE[self.pokemon.item.name] if self.pokemon.item.name in PLATE_TYPE else 'ノーマル']
            else:
                return self.added_types + \
                    [t for t in self.pokemon._types if t not in self.lost_types + self.added_types]

    @property
    def boost_source(self) -> BoostSource:
        return self._boost_source

    @boost_source.setter
    def boost_source(self, v: BoostSource):
        self._boost_source = v
        if v.value:
            a = [0] + [v * self.rank_modifier(i)
                       for i, v in enumerate(self.pokemon.stats[1:])]
            self.boosted_idx = a.index(max(a))
        else:
            self.boosted_idx = None

    @property
    def first_act(self):
        """先手で行動していたらTrue"""
        return self.idx == self.battle.turn_mgr.first_player_idx

    def rank_modifier(self, stat_idx: int) -> float:
        """ランク補正値. idx: 0~7 (H,A,B,C,D,S,命中,回避)"""
        if self.rank[stat_idx] >= 0:
            return (self.rank[stat_idx]+2)/2
        else:
            return 2/(2-self.rank[stat_idx])

    def activate_ability(self, move: Move | None = None, mode: str | None = None) -> bool:
        """特性を発動する"""
        return _activate_ability(self, move, mode)

    def activate_item(self, move: Move | None = None) -> bool:
        """アイテムを発動する"""
        return _activate_item(self, move)

    def activate_move_effect(self, move: Move) -> bool:
        """技の効果を発動する"""
        return _activate_move_effect(self, move)

    def apply_move_recoil(self, move: Move, label: str) -> bool:
        """技の反動の処理を行う"""
        return _apply_move_recoil(self, move, label)

    def process_tagged_move(self, move: Move, tag: str) -> bool:
        """技の追加処理を行う"""
        return _process_tagged_move(self, move, tag)

    def set_ailment(self,
                    ailment: Ailment,
                    move: Move | None = None,
                    bad_poison: bool = False,
                    ignore_shinpi: bool = False) -> bool:
        """
        状態異常を設定する

        Parameters
        ----------
        ailment : Ailment
            状態異常
        move : Move | None, optional
            指定された場合、技によって状態異常が付与されたとみなす, by default None
        bad_poison : bool, optional
            もうどくならTrue, by default False
        ignore_shinpi : bool, optional
            Trueならしんぴのまもりを考慮する, by default False

        Returns
        -------
        bool
            状態異常を設定できたらTrueを返す
        """
        if move is None:
            move = Move()
        return _set_ailment(self, ailment, move, bad_poison, ignore_shinpi)

    def set_condition(self,
                      condition: Condition,
                      count: int = 1,
                      move: Move | None = None) -> bool:
        """
        状態を設定する

        Parameters
        ----------
        condition : Condition
            状態
        count : int, optional
            状態のカウント(残りターン), by default 1
        move : Move | None, optional
            指定された場合、技による状態付与とみなす, by default None

        Returns
        -------
        bool
            設定できたらTrue
        """
        return _set_condition(self, condition, count, move)

    def add_condition_count(self,
                            condition: Condition,
                            v: int = 1) -> bool:
        """
        状態のカウントを加算する

        Parameters
        ----------
        condition : Condition
            状態
        v : int, optional
            変化量, by default 1

        Returns
        -------
        bool
            カウントを変更できたらTrue
        """
        return _add_condition_count(self, condition, v)

    def add_hp(self,
               value: int = 0,
               ratio: float | None = None,
               move: Move | None = None) -> bool:
        """
        HPを加算する

        Parameters
        ----------
        value : int, optional
            変化量, by default 0
        ratio : float | None, optional
            変化率, by default None
        move : Move | None, optional
            指定された場合、技による変化とみなす, by default None

        Returns
        -------
        bool
            HPを変更できたらTrue
        """
        if ratio is not None:
            value = int(self.pokemon.stats[0] * ratio)
        return _add_hp(self, value, move) if value else False

    def hp_drain_amount(self,
                        raw_amount: int,
                        from_opponent: bool | None = True) -> int:
        """
        補正後のHP吸収量を返す

        Parameters
        ----------
        raw_amount : int
            補正前のHP吸収量
        from_opponent : bool | None, optional
            Trueなら相手から吸収したとみなす, by default True

        Returns
        -------
        int
            補正後のHP吸収量
        """
        r = 1
        if self.pokemon.item.name == 'おおきなねっこ':
            r *= 5324/4096
        if from_opponent and self.opponent.ability.name == 'ヘドロえき':
            r *= -1
        return ut.round_half_up(raw_amount * r)

    def add_rank(self,
                 stat_idx: int | None = None,
                 value: int | None = None,
                 values: list[int] = [],
                 by_opponent: bool = False,
                 chain: bool = False) -> list[int]:
        """
        場のポケモンの能力ランクに指定した値を足す

        Parameters
        ----------
        stat_idx : int | None, optional
            0,1,2,3,4,5,6,7
            H,A,B,C,D,S,命中,回避
        value : int | None, optional
            変動量, by default None
        values : list[int], optional
            変動量のリスト, by default [0]*8
        by_opponent : bool, optional
            Trueなら相手による能力変化とみなす, by default False
        chain : bool, optional
            Falseならミラーアーマーやものまねハーブ等の処理を行わない, by default False

        Returns
        -------
        list[int]
            実際に変動したランクのリスト
        """
        if stat_idx is not None and value is not None:
            values = [0]*8
            values[stat_idx] = value
        return _add_rank(self, values, by_opponent, chain)

    def lose_item(self) -> None:
        self.pokemon.item.consume()
        self.battle.logger.append(TurnLog(self.battle.turn, self.idx, f"{self.pokemon.item.name_lost}消費"))

        # かるわざ発動
        if self.pokemon.ability.name == 'かるわざ' and not self.pokemon.item.active:
            self.activate_ability()

    def consume_item(self) -> None:
        self.lose_item()

        # きのみ関連の特性の発動
        if self.pokemon.item.name_lost[-2:] == 'のみ' and "berry" in self.pokemon.ability.tags:
            self.activate_ability()

    def defending_ability(self, move: Move | None = None) -> Ability:
        """
        防御側の有効な特性を返す

        Parameters
        ----------
        move : Move | None, optional
            攻撃技, by default None

        Returns
        -------
        Ability
            防御側の特性
        """
        attacker, defender = self.opponent, self.pokemon

        if not move or defender.item.name == 'とくせいガード' or \
                defender.ability.name in PokeDB.tagged_abilities["undeniable"]:
            return defender.ability

        if move.name in ['シャドーレイ', 'フォトンゲイザー', 'メテオドライブ'] or \
            attacker.ability.name in ['かたやぶり', 'ターボブレイズ', 'テラボルテージ'] or \
                (attacker.ability.name == 'きんしのちから' and move.category == MoveCategory.STA):
            return Ability()

        return defender.ability

    def effective_speed(self, masked: bool = False) -> int:
        """
        補正を考慮した素早さ実効値を返す

        Parameters
        ----------
        masked : bool, optional
            Trueなら観測可能な情報のみを考慮して計算する, by default False

        Returns
        -------
        int
            補正を考慮した素早さ実効値
        """
        return _effective_speed(self, masked)

    def contacts(self, move: Move) -> bool:
        """接触攻撃ならTrue"""
        return move and \
            "contact" in move.tags and \
            self.pokemon.ability.name != 'えんかく' and \
            self.pokemon.item.name != 'ぼうごパッド' and \
            not ("punch" in move.tags and self.pokemon.item.name == 'パンチグローブ')

    def can_receive_move_effect(self, move: Move | None) -> bool:
        """技の追加効果を受けることができる状態ならTrue"""
        return self.opponent.ability.name != 'ちからずく' and \
            self.defending_ability(move) != 'りんぷん' and \
            self.pokemon.item.name != 'おんみつマント' and \
            not self.battle.turn_mgr._hit_substitute

    def can_be_flinched(self):
        """ひるむことができる状態ならTrue"""
        return self.idx != self.battle.turn_mgr.first_player_idx and \
            self.pokemon.ability.name != 'せいしんりょく'

    def can_choose_move(self, move: Move) -> list[bool | str]:
        """技を選択できるならTrue"""
        return _can_choose_move(self, move)

    def is_floating(self) -> bool:
        """浮いている状態ならTrue"""
        if self.pokemon.item.name == 'くろいてっきゅう' or \
            self.count[Condition.ANTI_AIR] or \
                self.count[Condition.NEOHARU] or \
                self.battle.field_mgr.count[GlobalField.GRAVITY]:
            return False

        return 'ひこう' in self.types or \
            self.pokemon.ability.name == 'ふゆう' or \
            self.pokemon.item.name == 'ふうせん' or \
            self.count[Condition.MAGNET_RISE]

    def is_caught(self) -> bool:
        """捕まっている状態ならTrue"""
        if 'ゴースト' in self.types or \
            self.pokemon.ability.name == 'にげあし' or \
                self.pokemon.item.name == 'きれいなぬけがら':
            return False

        if self.count[Condition.SWITCH_BLOCK] or \
                self.count[Condition.BIND]:
            return True

        match self.opponent.ability.name:
            case 'ありじごく':
                return not self.is_floating()
            case 'かげふみ':
                return self.pokemon.ability.name != 'かげふみ'
            case 'じりょく':
                return 'はがね' in self.types

        return False

    def is_ability_protected(self) -> bool:
        """特性が上書きされない状態ならTrue"""
        return self.pokemon.ability.name in PokeDB.tagged_abilities["protected"] or \
            self.pokemon.item.name == 'とくせいガード'

    def is_item_removable(self):
        """アイテムを奪われる状態ならTrue"""
        return self.pokemon.name not in EXCLUSIVE_ITEM and \
            self.pokemon.ability.name != 'ねんちゃく' and \
            self.pokemon.item.name != 'ブーストエナジー' and \
            not (self.pokemon.name == 'アルセウス' and self.pokemon.item.name[-4:] == 'プレート') and \
            not (self.pokemon.name == 'ゲノセクト' and self.pokemon.item.name[-4:] == 'カセット')

    def is_overcoat(self, move: Move | None = None) -> bool:
        """ぼうじん状態ならTrue"""
        return self.pokemon.item.name == 'ぼうじんゴーグル' or \
            self.defending_ability(move) == 'ぼうじん'

    def is_nervous(self) -> bool:
        """きんちょうかん状態ならTrue"""
        return self.opponent.ability.name in ['きんちょうかん', 'じんばいったい']

    def is_blowable(self) -> bool:
        """強制交代可能ならTrue"""
        return bool(self.battle.switchable_indexes(self.idx)) and \
            self.pokemon.ability.name not in ['きゅうばん', 'ばんけん'] and \
            not self.count[Condition.NEOHARU]

    def reduce_sleep_count(self, by: int = 1):
        """眠りカウントを消費する"""
        self.pokemon.sleep_count = max(0, self.pokemon.sleep_count - by)
        self.battle.logger.append(
            TurnLog(self.battle.turn, self.idx, f"ねむり 残り{self.pokemon.sleep_count}ターン"))
        if self.pokemon.sleep_count == 0:
            self.set_ailment(Ailment.NONE)

    def rejected_items(self) -> list[str]:
        """観測情報から否定されるアイテムの一覧を返す"""
        if self.pokemon.item.observed:
            return []

        rejected_items = []

        for i in self.battle.selection_indexes[self.idx]:
            poke = self.player.team[i]
            if self.pokemon != poke and poke.item.observed:
                rejected_items.append(poke.item.name)

        expended_move_names = [move.name for move in self.expended_moves]
        if len(set(expended_move_names)) > 1:
            rejected_items += ['こだわりスカーフ', 'こだわりハチマキ', 'こだわりメガネ']

        if MoveCategory.STA in [move.category for move in self.expended_moves]:
            rejected_items.append('とつげきチョッキ')

        return list(set(rejected_items))
