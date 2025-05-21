from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Command, Phase
import pokebot.common.utils as ut
from pokebot.model import Pokemon, Move
from pokebot.logger import TurnLog

from pokebot.core.move_utils import effective_move_type

from .turn_methods.damage import _process_special_damage, _modify_damage
from .turn_methods.process_attack_move import _process_attack_move
from .turn_methods.process_status_move import _process_status_move
from .turn_methods.process_on_miss import _process_on_miss
from .turn_methods.process_protection import _process_protection
from .turn_methods.end_turn import _end_turn
from .turn_methods.advance_turn import _advance_turn
from .turn_methods.action_order import _update_action_order, update_speed_order, _estimate_opponent_speed
from .turn_methods.charge_move import _charge_move
from .turn_methods.flinch import _check_flinch
from .turn_methods.switch import _switch_pokemon, _land
from .turn_methods.can_execute_move import _can_execute_move
from .turn_methods.process_turn_action import _process_turn_action


class TurnManager:
    def __init__(self, battle: Battle):
        self.battle = battle

        self.breakpoint: list[str | None]
        self.scheduled_switch_commands: list[list[Command]]

        self.move: list[Move]
        self.move_succeeded: list[bool]
        self.damage_dealt: list[int]
        self.command: list[Command]
        self.switch_history: list[list[Command]]
        self.speed_order: list[PlayerIndex | int]
        self.move_speed: list[float]

        self.first_player_idx: PlayerIndex | int
        self._n_strikes: int
        self._second_player_has_act: bool
        self._koraeru: bool
        self._flinch: bool
        self._protecting_move: Move
        self._already_switched: list[bool]

        self._hit_substitute: bool
        self._move_was_negated_by_ability: bool
        self._move_was_mirrored: bool

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.selective_deepcopy(self, new)
        return new

    def init_game(self):
        self.breakpoint = [None, None]
        self.scheduled_switch_commands = [[], []]
        self.first_player_idx = 0

        self.init_turn()

    def init_turn(self):
        """ターン開始時に初期化"""
        self.battle.init_turn()

        self.move = [Move(), Move()]
        self.move_succeeded = [True, True]
        self.damage_dealt = [0, 0]
        self.command = [Command.NONE] * 2
        self.switch_history = [[], []]
        self.speed_order = [0, 1]
        self.move_speed = [0, 0]

        self._second_player_has_act = False
        self._koraeru = False
        self._flinch = False
        self._protecting_move = Move()
        self._already_switched = [False, False]

        self.init_act()

    def init_act(self):
        self._hit_substitute = False
        self._move_was_negated_by_ability = False
        self._move_was_mirrored = False

    @property
    def action_order(self) -> list[PlayerIndex | int]:
        return [self.first_player_idx, int(not self.first_player_idx)]

    def advance_turn(self, commands: list[Command], switch_commands: list[Command]):
        return _advance_turn(self, commands, switch_commands)

    def charge_move(self, atk: PlayerIndex | int, move: Move) -> bool:
        return _charge_move(self, atk, move)

    def process_attack_move(self, atk: PlayerIndex | int, move: Move, combo_count: int = 1):
        return _process_attack_move(self, atk, move, combo_count)

    def process_status_move(self, atk: PlayerIndex | int, move: Move):
        return _process_status_move(self, atk, move)

    def process_special_damage(self, atk: PlayerIndex | int, move: Move):
        return _process_special_damage(self, atk, move)

    def process_negating_ability(self, dfn: PlayerIndex | int):
        defender = self.battle.pokemons[dfn]
        def_mgr = self.battle.poke_mgrs[dfn]
        if defender.ability.name == 'かんそうはだ':
            def_mgr.add_hp(ratio=0.25)
        elif defender.ability.name == 'かぜのり':
            def_mgr.add_rank(1, +1)
        else:
            def_mgr.activate_ability()

    def process_protection(self, atk: PlayerIndex | int, move: Move) -> bool:
        return _process_protection(self, atk, move)

    def process_on_miss(self, atk: PlayerIndex | int, move: Move):
        return _process_on_miss(self, atk, move)

    def end_turn(self):
        return _end_turn(self)

    def modify_damage(self, atk: PlayerIndex | int):
        return _modify_damage(self, atk)

    def is_ejectpack_triggered(self, idx: PlayerIndex | int):
        return self.battle.pokemons[idx].item == "だっしゅつパック" and \
            self.battle.poke_mgrs[idx].rank_dropped and \
            self.battle.switchable_indexes(idx)

    def update_action_order(self):
        return _update_action_order(self)

    def update_speed_order(self):
        return update_speed_order(self)

    def estimate_opponent_speed(self, idx: PlayerIndex | int):
        return _estimate_opponent_speed(self, idx)

    def check_flinch(self, idx: PlayerIndex | int, move: Move) -> bool:
        """
        相手をひるませたらTrueを返す

        Parameters
        ----------
        idx : PlayerIndex | int
            攻撃側のプレイヤー番号
        move : Move
            攻撃技

        Returns
        -------
        bool
            相手をひるませたらTrue
        """
        return _check_flinch(self, idx, move)

    def consume_stellar(self, idx: PlayerIndex | int, move: Move):
        user = self.battle.pokemons[idx]
        user_mgr = self.battle.poke_mgrs[idx]
        move_type = effective_move_type(self.battle, idx, move)
        if self.damage_dealt[idx] and \
                user.terastal == 'ステラ' and \
                move_type not in user_mgr.consumed_stellar_types and \
                'テラパゴス' not in user.name:
            user_mgr.consumed_stellar_types.append(move_type)
            self.battle.logger.append(TurnLog(self.battle.turn, idx, f"ステラ {move_type}消費"))

    def switch_pokemon(self,
                       idx: PlayerIndex | int,
                       command: Command = Command.NONE,
                       switch: Pokemon | None = None,
                       switch_idx: int | None = None,
                       baton: dict = {},
                       landing: bool = True):

        if self.scheduled_switch_commands[idx]:
            # 予定されているコマンドを消費
            command = self.scheduled_switch_commands[idx].pop(0)
        elif command.is_switch:
            pass
        elif switch is not None:
            # コマンドに変換
            command = self.battle.to_command(idx, switch=switch)
        elif switch_idx is not None:
            # コマンドに変換
            command = self.battle.to_command(idx, switch_idx=switch_idx)
        else:
            # 方策関数からコマンドを取得
            self.battle.phase = Phase.SWITCH
            masked = self.battle.masked(idx, called=True)
            command = self.battle.players[idx].switch_command(masked)
            self.battle.phase = Phase.NONE

        self.switch_history[idx].append(command)

        return _switch_pokemon(self, idx, command, baton, landing)

    def land(self, idx: PlayerIndex | int):
        return _land(self, idx)

    def can_execute_move(self, idx: PlayerIndex | int, move: Move, tag: str = ""):
        return _can_execute_move(self, idx, move, tag)

    def process_turn_action(self, idx: PlayerIndex | int):
        return _process_turn_action(self, idx)
