from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.player.random_player import RandomPlayer

import time
from random import Random
import json
from copy import deepcopy

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Command, Mode, Phase
import pokebot.common.utils as ut
from pokebot.core import Pokemon, Move

from pokebot.logger import Logger
from pokebot.turn import TurnManager
from pokebot.pokemon import ActivePokemonManager
from pokebot.field import FieldManager
from pokebot.damage import DamageManager

from .methods.winner import _winner
from .methods.command import _to_command, _command_to_str, _available_commands
from .methods.mask import _mask


class Battle:
    def __init__(self,
                 player1: RandomPlayer,
                 player2: RandomPlayer,
                 mode: Mode = Mode.SIM,
                 n_selection: int = 3,
                 open_sheet: bool = False,
                 seed: int | None = None):

        if mode == Mode.SIM:
            n_selection = min(n_selection, len(player1.team), len(player2.team))
        elif mode == Mode.OFFLINE:
            n_selection = len(player1.team)

        if seed is None:
            seed = int(time.time())

        if mode != Mode.SIM:
            open_sheet = False

        self.player: list[RandomPlayer] = [player1, player2]
        self.mode: Mode = mode
        self.n_selection: int = n_selection
        self.open_sheet: bool = open_sheet
        self.seed: int = seed

        self.random: Random = Random(self.seed)
        self.logger: Logger = Logger()
        self.turn_mgr: TurnManager = TurnManager(self)
        self.poke_mgr: list[ActivePokemonManager] = [ActivePokemonManager(self, PlayerIndex(i)) for i in range(2)]
        self.field_mgr: FieldManager = FieldManager(self)
        self.damage_mgr: DamageManager = DamageManager(self)

        self._winner: PlayerIndex | None
        self.selection_indexes: list[list[int]]
        self.turn: int
        self.phase: Phase
        self.call_count: list[int]

        # プレイヤーに番号を割り振る
        for i in range(2):
            self.player[i].idx = PlayerIndex(i)

        # 試合のリセット
        self.init_game()

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
            "player", "random", "logger", "turn_mgr",
            "poke_mgr", "field_mgr", "damage_mgr"
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
        for mgr in self.poke_mgr:
            mgr.init_game()
        self.field_mgr.init_game()

        # 選出
        self.select_pokemon()

        # オープンシート制なら情報開示
        if self.open_sheet:
            for player in self.player:
                for p in player.team:
                    p.ability.observed = True
                    p.item.observed = True
                    for move in p.moves:
                        move.observed = True

    def init_turn(self):
        self.phase = Phase.NONE
        self.call_count = [0, 0]

    @property
    def pokemon(self) -> list[Pokemon]:
        return [self.poke_mgr[i].pokemon for i in range(2)]

    def select_pokemon(self):
        """ポケモンを選出する"""
        self.phase = Phase.SELECTION

        for idx, player in enumerate(self.player):
            # コマンドの取得
            match self.mode:
                case Mode.SIM:
                    masked = self.masked(PlayerIndex(idx))
                    commands = player.selection_command(masked)
                case Mode.OFFLINE:
                    commands = Command.selection_commands()[:len(player.team)]

            self.selection_indexes[idx] = [cmd.index for cmd in commands]

        self.phase = Phase.NONE

    def mask(self, perspective: PlayerIndex):
        """プレイヤー視点に相当するように非公開情報を隠蔽・補完する"""
        if not self.open_sheet:
            return _mask(self, perspective)

    def masked(self, perspective: PlayerIndex, called: bool = False) -> Battle:
        """非公開情報を隠蔽したコピーを返す"""
        battle = deepcopy(self)

        # 管理クラスに複製したbattleを再設定する
        for mgr in [battle.turn_mgr, battle.poke_mgr[0], battle.poke_mgr[1], battle.field_mgr, battle.damage_mgr]:
            mgr.battle = battle

        battle.mask(perspective)

        if called:
            battle.call_count[perspective] += 1

        return battle

    def write(self, filepath: str):
        d = {
            "seed": self.seed,
            "mode": self.mode.value,
            "teams": [[poke.dump() for poke in player.team] for player in self.player],
            "selection_indexes": self.selection_indexes,
            "command_logs": [log.dump() for log in self.logger.command_logs]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json.dumps(d, ensure_ascii=False))

    def selected_pokemons(self, idx: PlayerIndex) -> list[Pokemon]:
        return [self.player[idx].team[i] for i in self.selection_indexes[idx]]

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

    def winner(self, TOD: bool = False) -> PlayerIndex | None:
        """
        勝敗を判定し、勝利したプレイヤー番号を返す

        Parameters
        ----------
        TOD : bool, optional
            TrueならTOD判定を行う, by default False
        """
        return _winner(self, TOD)

    def switchable_indexes(self, idx: PlayerIndex) -> list[int]:
        """交代可能なポケモンのインデックスのリストを返す"""
        return [i for i in self.selection_indexes[idx] if not self.player[idx].team[i].active]

    def can_terastallize(self, idx: PlayerIndex) -> bool:
        return not any(p.terastal for p in self.selected_pokemons(idx))

    def to_command(self: Battle,
                   idx: PlayerIndex,
                   selection_idx: int | None = None,
                   switch: Pokemon | None = None,
                   switch_idx: int | None = None,
                   move: Move | None = None,
                   terastal: bool = False) -> Command:
        if switch in self.player[idx].team:
            switch_idx = self.player[idx].team.index(switch)

        return _to_command(self, idx, selection_idx, switch_idx, move, terastal)

    def command_to_str(self: Battle,
                       idx: PlayerIndex,
                       command: Command) -> str:
        return _command_to_str(self, idx, command)

    def available_commands(self,
                           idx: PlayerIndex,
                           phase: Phase | None = None) -> list[Command]:
        if phase is None:
            phase = self.phase
        return _available_commands(self, idx, phase)

    @property
    def action_order(self) -> list[PlayerIndex]:
        return self.turn_mgr.action_order
