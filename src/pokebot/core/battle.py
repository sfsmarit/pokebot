from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.player import Player

import time
from random import Random
import json
from copy import deepcopy

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Command, Phase, Time
import pokebot.common.utils as ut
from pokebot.model import Pokemon, Move
from pokebot.logger import Logger, DamageLog

from .turn_manager import TurnManager
from .pokemon_manager import ActivePokemonManager
from .field_manager import FieldManager
from .damage_manager import DamageManager
from .battle_methods.winner import _winner
from .battle_methods.command import _to_command, _command_to_str, _available_commands
from .battle_methods.mask import _mask


class Battle:
    def __init__(self,
                 player1: Player,
                 player2: Player,
                 n_selection: int = 3,
                 open_sheet: bool = False,
                 seed: int | None = None):

        if seed is None:
            seed = int(time.time())

        self.players: list[Player] = [player1, player2]
        self.n_selection: int = n_selection
        self.open_sheet: bool = open_sheet
        self.seed: int = seed

        self.random: Random = Random(self.seed)
        self.logger: Logger = Logger()
        self.turn_mgr: TurnManager = TurnManager(self)
        self.poke_mgrs: list[ActivePokemonManager] = [ActivePokemonManager(self, i) for i in range(2)]
        self.field_mgr: FieldManager = FieldManager(self)
        self.damage_mgr: DamageManager = DamageManager(self)

        self._winner: PlayerIndex | int | None
        self.selection_indexes: list[list[int]]
        self.turn: int
        self.phase: Phase
        self.call_count: list[int]

        self.game_start_time: float
        self.turn_start_time: float
        self.selection_input_time: float = 10
        self.action_input_time: float = 10
        self.switch_input_time: float = 3

        # プレイヤーに番号を割り振る
        for i in range(2):
            self.players[i].idx = i

        # 試合のリセット
        self.init_game()

        # 選出
        self.select_pokemon()

        ''' TODO ダメージからBattle再現
        # 引数に指定があれば、ダメージ発生時の状況に上書きする
        if damage:
            self.pokemon = deepcopy(damage.pokemons)
            self.stellar[damage.attack_player_idx] = damage.stellar.copy()
            self.condition = deepcopy(damage.condition)
        '''

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new, keys_to_deepcopy=[
            "players", "random", "logger", "turn_mgr",
            "poke_mgrs", "field_mgr", "damage_mgr"
        ])

        # 乱数の隠蔽
        new.random.seed(self.seed)

        return new

    def init_game(self):
        """試合開始前の状態に初期化する"""
        self._winner = None
        self.selection_indexes = [[], []]
        self.turn = -1

        self.logger.clear()
        self.turn_mgr.init_game()
        for mgr in self.poke_mgrs:
            mgr.init_game()
        self.field_mgr.init_game()

        # オープンシート制なら情報開示
        if self.open_sheet:
            for player in self.players:
                for p in player.team:
                    p.ability.observed = True
                    p.item.observed = True
                    for move in p.moves:
                        move.observed = True

        self.game_start_time = time.time()

    def init_turn(self):
        self.phase = Phase.NONE
        self.call_count = [0, 0]
        self.turn_start_time = time.time()

    def game_time(self) -> float:
        """残りの試合時間"""
        elapsed_time = time.time() - self.game_start_time
        return Time.GAME.value - elapsed_time

    def thinking_time(self) -> float:
        """残りのターン持ち時間"""
        match self.phase:
            case Phase.SELECTION:
                return Time.SELECTION.value - self.selection_input_time - (time.time()-self.turn_start_time)
            case Phase.ACTION | Phase.SWITCH:
                return Time.COMMAND.value - self.action_input_time - (time.time()-self.turn_start_time)
            case _:
                return 1e10

    @property
    def pokemons(self) -> list[Pokemon]:
        pokemons = [None, None]
        for idx, player in enumerate(self.players):
            for p in player.team:
                if p.active:
                    pokemons[idx] = p  # type: ignore
                    break
        return pokemons  # type: ignore

    @property
    def action_order(self) -> list[PlayerIndex | int]:
        return self.turn_mgr.action_order

    def select_pokemon(self):
        """ポケモンを選出する"""
        self.phase = Phase.SELECTION

        # コマンドの取得
        for idx, player in enumerate(self.players):
            commands = player.selection_commands(self.masked(idx))
            self.selection_indexes[idx] = [cmd.index for cmd in commands]

        self.phase = Phase.NONE

    def mask(self, perspective: PlayerIndex | int):
        """プレイヤー視点に相当するように非公開情報を隠蔽・補完する"""
        if not self.open_sheet:
            return _mask(self, perspective)

    def masked(self, perspective: PlayerIndex | int, called: bool = False) -> Battle:
        """非公開情報を隠蔽したコピーを返す"""
        battle = deepcopy(self)

        # 管理クラスに複製したbattleを再設定する
        for mgr in [battle.turn_mgr, battle.poke_mgrs[0], battle.poke_mgrs[1], battle.field_mgr, battle.damage_mgr]:
            mgr.battle = battle

        battle.mask(perspective)

        if called:
            battle.call_count[perspective] += 1

        return battle

    def write(self, filepath: str):
        d = {
            "seed": self.seed,
            "teams": [[poke.dump() for poke in player.team] for player in self.players],
            "selection_indexes": self.selection_indexes,
            "command_logs": [log.dump() for log in self.logger.command_logs]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json.dumps(d, ensure_ascii=False))

    def selected_pokemons(self, idx: PlayerIndex | int) -> list[Pokemon]:
        return [self.players[idx].team[i] for i in self.selection_indexes[idx]]

    def advance_turn(self,
                     commands: list[Command] = [Command.NONE]*2,
                     switch_commands: list[Command] = [Command.NONE]*2):
        """
        盤面を1ターン進める

        Parameters
        ----------
        commands : list[int], optional
            ターン開始時に両プレイヤーが入力するコマンド, by default [None]*2
        switch_commands : list[int], optional
            自由交代時に両プレイヤーが入力するコマンド, by default [None]*2
        """
        self.turn_mgr.advance_turn(commands, switch_commands)
        return

    def winner(self, TOD: bool = False) -> PlayerIndex | int | None:
        """
        勝敗を判定し、勝利したプレイヤー番号を返す

        Parameters
        ----------
        TOD : bool, optional
            TrueならTOD判定を行う, by default False
        """
        return _winner(self, TOD)

    def switchable_indexes(self, idx: PlayerIndex | int) -> list[int]:
        """交代可能なポケモンのインデックスのリストを返す"""
        return [i for i in self.selection_indexes[idx] if
                not self.players[idx].team[i].active and self.players[idx].team[i].hp]

    def can_terastallize(self, idx: PlayerIndex | int) -> bool:
        return not any(p.terastal for p in self.selected_pokemons(idx))

    def to_command(self: Battle,
                   idx: PlayerIndex | int,
                   selection_idx: int | None = None,
                   switch: Pokemon | None = None,
                   switch_idx: int | None = None,
                   move: Move | None = None,
                   terastal: bool = False) -> Command:
        if switch in self.players[idx].team:
            switch_idx = self.players[idx].team.index(switch)

        return _to_command(self, idx, selection_idx, switch_idx, move, terastal)

    def command_to_str(self: Battle,
                       idx: PlayerIndex | int,
                       command: Command) -> str:
        return _command_to_str(self, idx, command)

    def available_commands(self,
                           idx: PlayerIndex | int,
                           phase: Phase | None = None) -> list[Command]:
        if phase is None:
            phase = self.phase
        return _available_commands(self, idx, phase)

    def restore_from_damage_log(self, log: DamageLog):
        battle = deepcopy(self)
        battle.turn = log.turn
        for i in range(2):
            battle.pokemons[i].load(log.pokemons[i])
            battle.poke_mgrs[i].load(log.poke_mgrs[i])
        battle.damage_mgr.critical = log.critical
        battle.field_mgr.load(log.field_mgr)
        return battle
