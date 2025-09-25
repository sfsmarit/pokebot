import random
import json
import time
from typing import Self

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Command
import pokebot.common.utils as ut
from pokebot.pokedb import Pokemon
from pokebot.core import Battle

from .player_methods.game import _game
from .player_methods.replay import _replay
from .player_methods.complement import _complement_opponent_selection, \
    _complement_opponent_switch, _complement_opponent_move, _complement_opponent_kata
from .player_methods.estimate import estimate_attack, estimate_defence, estimate_speed
from .player_methods.max_damage_command import _max_damage_command


class Player:
    """対戦シミュレーションにのみ対応したプレイヤークラス"""

    def __init__(self):
        self.team: list[Pokemon] = []
        self.n_game: int = 0
        self.n_won: int = 0
        self.rating: float = 1500
        self.idx: PlayerIndex | int

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new, keys_to_deepcopy=["team"])
        return new

    def init_game(self):
        for poke in self.team:
            poke.init_game()

    def game(self,
             opponent: Self,
             n_selection: int = 3,
             open_sheet: bool = False,
             seed: int | None = None,
             max_turn: int = 100,
             display_log: bool = True,
             is_test: bool = False) -> Battle:
        """
        試合を行う

        Parameters
        ----------
        opponent : Player
            対戦相手のプレイヤー
        mode : BattleMode, optional
            対戦モード, by default BattleMode.SIM
        n_selection : int, optional
            選出するポケモンの数, by default 3
        open_sheet : bool, optional
            Trueならパーティの情報を開示する, by default False
        seed : int | None, optional
            乱数シード, by default None
        video_id : int, optional
            ビデオキャプチャのデバイスID
            BattleMode.OFFLINE/ONLINEでのみ使用, by default 0
        display_log : bool, optional
            Trueならログを表示する, by default True
        is_test : bool, optional
            Trueなら確率的事象を必ず発生させるテスト用フラグ, by default False

        Returns
        -------
        Battle
            試合終了後の盤面
        """
        n_selection = min(n_selection, len(self.team), len(opponent.team))

        if seed is None:
            seed = int(time.time())

        return _game(self, opponent, n_selection, open_sheet, seed, max_turn, display_log, is_test)

    def save_team(self, filename: str):
        with open(filename, 'w', encoding='utf-8') as fout:
            d = {}
            for i, p in enumerate(self.team):
                d[str(i)] = p.dump()
                print(f"{i+1} {p}\n")
            fout.write(json.dumps(d, ensure_ascii=False))

    def load_team(self, filename: str):
        with open(filename, encoding='utf-8') as fin:
            dict = json.load(fin)
            self.team = []
            for i, d in enumerate(dict.values()):
                p = Pokemon()
                p.load(d)
                self.team.append(p)
                print(f"{i+1} {p}\n")

    def selection_commands(self, battle: Battle) -> list[Command]:
        """選出の方策関数"""
        return self._random_select(battle)

    def action_command(self, battle: Battle) -> Command:
        """ターン行動の方策関数"""
        return self._random_command(battle)

    def switch_command(self, battle: Battle) -> Command:
        """自由交代の方策関数"""
        return self._random_command(battle)

    def _random_select(self, battle: Battle) -> list[Command]:
        return random.sample(Command.selection_commands()[:len(self.team)], battle.n_selection)

    def _random_command(self, battle: Battle) -> Command:
        return random.choice(battle.available_commands(self.idx))

    def max_damage_command(self, battle: Battle) -> Command:
        return _max_damage_command(self, battle)

    def complement_opponent_selection(self, battle: Battle):
        return _complement_opponent_selection(self, battle)

    def complement_opponent_switch(self, battle: Battle):
        return _complement_opponent_switch(self, battle)

    def complement_opponent_move(self, battle: Battle):
        return _complement_opponent_move(self, battle)

    def complement_opponent_kata(self,
                                 poke: Pokemon,
                                 kata: str = '',
                                 overwrite_nature: bool = True,
                                 overwrite_ability: bool = True,
                                 overwrite_item: bool = True,
                                 overwrite_terastal: bool = True,
                                 overwrite_move: bool = True,
                                 overwrite_effort: bool = True):
        return _complement_opponent_kata(poke, kata, overwrite_nature, overwrite_ability, overwrite_item,
                                         overwrite_terastal, overwrite_move, overwrite_effort)

    def update_rating(self, opponent: Self, won: bool = True):
        players = [self, opponent]
        EAs = [1 / (1+10**((players[not i].rating-players[i].rating)/400)) for i in range(2)]
        for i in range(2):
            players[i].rating += 32 * ((won+i) % 2 - EAs[i])

    @classmethod
    def advance_turn(cls, battle: Battle, display_log: bool):
        """
        盤面を1ターン進める

        Parameters
        ----------
        battle : Battle
        mute : bool
            Trueなら画面にログを表示する
        """
        battle.advance_turn()

        # ログ表示
        if display_log:
            print(f"ターン{battle.turn}")
            for idx in battle.action_order:
                print(
                    f"\tPlayer {int(idx)}",
                    "[" + ", ".join(battle.logger.get_turn_log(battle.turn, idx)) + "]",
                    "{" + ", ".join(battle.logger.get_damage_log(battle.turn, idx)) + "}",
                )

    @classmethod
    def replay(cls, filepath: str, display_log: bool = True) -> Battle:
        """
        ログファイルの対戦をリプレイする

        Parameters
        ----------
        filepath : str
            ログファイルのパス
        mute : bool, optional
            Player.advance_turn()のmute設定, by default True

        Returns
        -------
        Battle
            リプレイ後の盤面
        """
        return _replay(cls, filepath, display_log)

    def estimate_opponent_stats(self, battle: Battle):
        """相手が選出したポケモンのステータスとアイテムを推定値に置き換える
        Parameters
        ----------
        battle: Battle

        Returns
        ----------
            True: 更新が行われた、または現状のままで矛盾しない
            False: 推定失敗
        """
        opp = int(not self.idx)

        # 相手の全選出を対象とする
        for poke in battle.selected_pokemons(opp):
            # 素早さ、火力、耐久の順に推定
            print(f"\t\tステータス推定\t{poke.name} : {poke.nature} {poke.effort} {poke.item}", end='')
            for stat_idx in [5, 1, 3, 2, 4]:
                match stat_idx:
                    case 1 | 3:
                        estimate_attack(self, battle, poke, stat_idx, False)
                    case 2 | 4:
                        estimate_defence(self, battle, poke, stat_idx, False)
                    case 5:
                        estimate_speed(poke)
            print(f" -> {poke.nature} {poke.effort} {poke.item}")
