from typing import Self

import time
from random import Random
from copy import deepcopy
import json

from pokebot.utils import copy_utils as copyut
from pokebot.utils.enums import Command, Stat

from pokebot.model import Pokemon, Move, Field

from pokebot.player import Player

from .event import Event, Interrupt, EventManager, EventContext
from .player_state import PlayerState
from .logger import Logger
from .damage import DamageCalculator, DamageContext
from .global_field import GlobalFieldManager
from .side_field import SideFieldManager
from .pokedb import PokeDB


class Battle:
    def __init__(self,
                 players: list[Player],
                 seed: int | None = None) -> None:

        if seed is None:
            seed = int(time.time())

        self.players: list[Player] = players
        self.seed: int = seed

        self.turn: int = -1
        self.winner_idx: int | None = None

        self.events = EventManager(self)
        self.logger = Logger()
        self.random = Random(self.seed)
        self.damage_calculator: DamageCalculator = DamageCalculator()

        self.states: list[PlayerState] = [PlayerState() for _ in players]
        self.field: GlobalFieldManager = GlobalFieldManager(self.events, self.players)
        self.sides: list[SideFieldManager] = [SideFieldManager(self.events, pl) for pl in self.players]

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        copyut.fast_copy(self, new, keys_to_deepcopy=[
            "players", "events", "logger", "random", "damage_calculator",
            "states", "field", "sides"
        ])

        # 複製したインスタンスが複製後を参照するように再代入する
        new.events.update_reference(new)
        new.field.update_reference(new.events, new.players)
        for i, side in enumerate(new.sides):
            side.update_reference(new.events, new.players[i])

        # 乱数の隠蔽
        new.random.seed(int(time.time()))

        return new

    def state(self, player: Player) -> PlayerState:
        return self.states[self.players.index(player)]

    def side(self, player: Player) -> SideFieldManager:
        return self.sides[self.players.index(player)]

    @property
    def actives(self) -> list[Pokemon]:
        return [self.active(pl) for pl in self.players]

    @property
    def weather(self) -> Field:
        return self.field.fields["weather"]

    @property
    def terrain(self) -> Field:
        return self.field.fields["terrain"]

    def export_log(self, file):
        data = {
            "seed": self.seed,
            "players": [],
        }

        for player, state in zip(self.players, self.states):
            data["players"].append({
                "name": player.name,
                "selection_indexes": state.selected_idxes,
                "commands": {},
                "team": [mon.dump() for mon in player.team],
            })

        for log in self.logger.command_logs:
            data["players"][log.player_idx]["commands"].setdefault(
                str(log.turn), []).append(log.command.name)

        with open(file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=4))

    @classmethod
    def reconstruct_from_log(cls, file) -> Self:
        with open(file, encoding="utf-8") as f:
            data = json.load(f)

        new = cls(
            [Player(), Player()],
            seed=data["seed"],
        )

        for i, (player, state) in enumerate(zip(new.players, new.states)):
            player_data = data["players"][i]
            player.name = player_data["name"]
            state.selected_idxes = player_data["selection_indexes"]

            for p in player_data["team"]:
                mon = PokeDB.reconstruct_pokemon_from_log(p)
                player.team.append(mon)

            for t, command_names in player_data["commands"].items():
                for s in command_names:
                    command = Command[s]
                    new.reserve_command(player, command, turn=int(t))

        return new

    def masked(self, perspective: Player) -> tuple[Self, Player]:
        # TODO mask
        new = deepcopy(self)
        new_player = new.players[self.players.index(perspective)]
        return new, new_player

    def active(self, player: Player) -> Pokemon:
        if (i := self.state(player).active_idx) is not None:
            return player.team[i]
        return None  # type: ignore

    def selected(self, player: Player) -> list[Pokemon]:
        return [player.team[i] for i in self.state(player).selected_idxes]

    def init_turn(self):
        for state in self.states:
            state.reset_turn()
        self.turn += 1

    def find_player(self, mon: Pokemon) -> Player:
        for player in self.players:
            if mon in player.team:
                return player
        raise Exception("Player not found.")

    def find_player_index(self, mon: Pokemon) -> int:
        for i, player in enumerate(self.players):
            if mon in player.team:
                return i
        raise Exception("Player not found.")

    def team_idx(self, mon: Pokemon) -> int:
        player = self.find_player(mon)
        return player.team.index(mon)

    def foe(self, active: Pokemon) -> Pokemon:
        actives = [self.active(pl) for pl in self.players]
        return actives[not actives.index(active)]

    def rival(self, player: Player) -> Player:
        return self.players[not self.players.index(player)]

    def can_use_terastal(self, player: Player) -> bool:
        return all(mon.can_terastallize() for mon in self.selected(player))

    def get_available_selection_commands(self, player: Player) -> list[Command]:
        return Command.selection_commands()[:len(player.team)]

    def get_available_switch_commands(self, player: Player) -> list[Command]:
        return [cmd for mon, cmd in zip(player.team, Command.switch_commands())
                if mon in self.selected(player) and
                mon is not self.active(player)]

    def get_available_action_commands(self, player: Player) -> list[Command]:
        n = len(self.active(player).moves)

        # 通常技
        commands = Command.move_commands()[:n]

        # テラスタル
        if self.can_use_terastal(player):
            commands += Command.terastal_commands()[:n]

        # わるあがき
        if not commands:
            commands = [Command.STRUGGLE]

        # 交代コマンド
        commands += self.get_available_switch_commands(player)

        return commands

    def reserve_command(self, player: Player, command: Command, turn: int | None = None):
        if turn is None:
            turn = self.turn
        self.state(player).reserved_commands.append(command)
        idx = self.players.index(player)
        self.logger.add_command_log(self.turn, idx, command)

    def get_turn_logs(self, turn: int | None = None) -> dict[Player, list[str]]:
        if turn is None:
            turn = self.turn
        return {pl: self.logger.get_turn_logs(turn, i) for i, pl in enumerate(self.players)}

    def get_damage_logs(self, turn: int | None = None) -> dict[Player, list[str]]:
        if turn is None:
            turn = self.turn
        return {pl: self.logger.get_damage_logs(turn, i) for i, pl in enumerate(self.players)}

    def to_player_idxes(self, source: Player | list[Player] | Pokemon | None) -> list[int]:
        if isinstance(source, Player):
            return [self.players.index(source)]
        if isinstance(source, list):
            return [self.players.index(pl) for pl in source]
        if isinstance(source, Pokemon):
            return [self.players.index(self.find_player(source))]
        if source is None:
            return list(range(len(self.players)))
        return []

    def add_turn_log(self, source: Player | list[Player] | Pokemon | None, text: str):
        for idx in self.to_player_idxes(source):
            self.logger.add_turn_log(self.turn, idx, text)

    def add_damage_log(self, source: Player | list[Player] | Pokemon | None, text: str):
        for idx in self.to_player_idxes(source):
            self.logger.add_damage_log(self.turn, idx, text)

    def calc_effective_speed(self, mon: Pokemon) -> int:
        return self.events.emit(Event.ON_CALC_SPEED, mon.S, EventContext(mon))  # type: ignore

    def get_speed_order(self) -> list[Pokemon]:
        speeds = [self.calc_effective_speed(p) for p in self.actives]
        if speeds[0] == speeds[1]:
            actives = self.active.copy()
            self.random.shuffle(actives)
        else:
            paired = sorted(zip(speeds, self.actives),
                            key=lambda pair: pair[0], reverse=True)
            _, actives = zip(*paired)
        return actives

    def get_action_order(self) -> list[Pokemon]:
        actives, speeds = [], []
        for i, mon in enumerate(self.actives):
            if self.states[i].has_switched:
                continue

            mon = self.actives[i]
            speed = self.calc_effective_speed(mon)

            command = self.states[i].reserved_commands[-1]
            move = self.command_to_move(self.players[i], command)
            ctx = EventContext(mon, move)
            action_speed = self.events.emit(Event.ON_CALC_ACTION_SPEED, 0, ctx)

            total_speed = action_speed + speed*1e-5  # type: ignore
            speeds.append(total_speed)
            actives.append(mon)

        # Sort by speed
        if len(actives) > 1:
            paired = sorted(zip(speeds, actives),
                            key=lambda pair: pair[0], reverse=True)
            _, actives = zip(*paired)

        return actives

    def TOD_score(self, player: Player, alpha: float = 1):
        n_alive, total_max_hp, total_hp = 0, 0, 0
        for mon in self.selected(player):
            total_max_hp += mon.max_hp
            total_hp += mon.hp
            if mon.hp:
                n_alive += 1
        return n_alive + alpha * total_hp / total_max_hp

    def winner(self) -> Player | None:
        if self.winner_idx is not None:
            return self.players[self.winner_idx]

        TOD_scores = [self.TOD_score(pl) for pl in self.players]
        if 0 in TOD_scores:
            loser_idx = TOD_scores.index(0)
            self.winner_idx = int(not loser_idx)
            self.add_turn_log(self.players[self.winner_idx], "勝ち")
            self.add_turn_log(self.players[loser_idx], "負け")
            return self.players[self.winner_idx]

        return None

    def run_selection(self):
        for player, state in zip(self.players, self.states):
            if not state.selected_idxes:
                commands = player.choose_selection_commands(self)
                state.selected_idxes = [c.idx for c in commands]

    def check_hit(self, source: Pokemon, move: Move) -> bool:
        accuracy = self.events.emit(
            Event.ON_CALC_ACCURACY,
            move.data.accuracy,
            EventContext(source, move),
        )
        return 100*self.random.random() < accuracy  # type: ignore

    def run_move(self, mon: Pokemon, move: Move):
        foe = self.foe(mon)

        # 技のハンドラを登録
        move.register_handlers(self.events, mon)

        self.add_turn_log(mon, f"{move.name}")

        # 行動成功判定
        self.events.emit(Event.ON_TRY_ACTION, ctx=EventContext(mon))

        # 発動成功判定
        self.events.emit(Event.ON_TRY_MOVE, ctx=EventContext(mon))

        mon.field_status.executed_move = move

        # TODO 命中判定
        self.check_hit(mon, move)

        # 無効判定
        self.events.emit(Event.ON_TRY_IMMUNE, ctx=EventContext(mon))

        # ダメージ計算
        damage = self.calc_damage(mon, move)

        # HPコストの支払い
        self.events.emit(Event.ON_PAY_HP, ctx=EventContext(mon))

        # ダメージ修正
        damage = self.events.emit(Event.ON_MODIFY_DAMAGE, value=damage, ctx=EventContext(mon))

        if damage:
            # ダメージ付与
            self.modify_hp(foe, -damage)

        self.events.emit(Event.ON_HIT, ctx=EventContext(mon))

        # ダメージを与えたときの処理
        if damage:
            self.events.emit(Event.ON_DAMAGE, ctx=EventContext(mon))

        move.unregister_handlers(self.events, mon)

    def command_to_move(self, player: Player, command: Command) -> Move:
        if command == Command.STRUGGLE:
            return PokeDB.create_move("わるあがき")
        elif command.is_zmove():
            return PokeDB.create_move("わるあがき")
        else:
            return self.active(player).moves[command.idx]

    def modify_hp(self, target: Pokemon, v: int = 0, r: float = 0) -> bool:
        if r:
            v = int(target.max_hp * r)
        if v and (v := target.modify_hp(v)):
            self.add_turn_log(self.find_player(target),
                              f"HP {'+' if v >= 0 else ''}{v} >> {target.hp}")
        return bool(v)

    def modify_stat(self, target: Pokemon, stat: Stat, v: int, by_foe: bool = False) -> bool:
        if v and (v := target.modify_stat(stat, v)):
            self.add_turn_log(self.find_player(target),
                              f"{stat}{'+' if v >= 0 else ''}{v}")
            self.events.emit(Event.ON_MODIFY_STAT, value=v,
                             ctx=EventContext(target, by_foe=by_foe))
        return bool(v)

    def calc_damage(self,
                    attacker: Pokemon,
                    move: Move | str,
                    critical: bool = False,
                    self_harm: bool = False,
                    ) -> int:
        damages = self.calc_damages(attacker, move, critical, self_harm)
        return self.random.choice(damages)

    def calc_damages(self,
                     attacker: Pokemon,
                     move: Move | str,
                     critical: bool = False,
                     self_harm: bool = False,
                     ) -> list[int]:
        if isinstance(move, str):
            move = PokeDB.create_move(move)
        defender = attacker if self_harm else self.foe(attacker)
        ctx = DamageContext(critical, self_harm)
        return self.damage_calculator.single_hit_damages(self.events, attacker, defender, move, ctx)

    def has_interrupt(self) -> bool:
        return any(state.interrupt != Interrupt.NONE for state in self.states)

    def override_interrupt(self, flag: Interrupt, only_first: bool = True):
        for mon in self.get_speed_order():
            player = self.find_player(mon)
            if self.state(player).interrupt == Interrupt.REQUESTED:
                self.state(player).interrupt = flag
                if only_first:
                    return

    def run_switch(self, player: Player, new: Pokemon, emit: bool = True):
        # 割り込みフラグを破棄
        self.state(player).interrupt = Interrupt.NONE

        # 退場
        old = self.active(player)
        if old is not None:
            self.events.emit(Event.ON_SWITCH_OUT, ctx=EventContext(old))
            old.switch_out(self.events)
            self.add_turn_log(player, f"{old.name} {'交代' if old.hp else '瀕死'}")

        # 入場
        self.state(player).active_idx = player.team.index(new)
        new.switch_in(self.events)
        self.add_turn_log(player, f"{new.name} 着地")

        # ポケモンが場に出た時の処理
        if emit:
            self.events.emit(Event.ON_SWITCH_IN, ctx=EventContext(new))

            # リクエストがなくなるまで再帰的に交代する
            while self.has_interrupt():
                flag = Interrupt.EJECTPACK_ON_AFTER_SWITCH
                self.override_interrupt(flag)
                self.run_interrupt_switch(flag)

        # その他の処理
        self.state(player).has_switched = True

    def run_initial_switch(self):
        # ポケモンを場に出す
        for player in self.players:
            new = self.selected(player)[0]
            self.run_switch(player, new, emit=False)

        # ポケモンが場に出たときの処理は、両者の交代が完了した後に行う
        self.events.emit(Event.ON_SWITCH_IN)

        # だっしゅつパックによる割り込みフラグを更新
        self.override_interrupt(Interrupt.EJECTPACK_ON_START)

    def run_interrupt_switch(self, flag: Interrupt, emit_on_each_switch=True):
        switched_players = []

        for player in self.players:
            if self.state(player).interrupt != flag:
                continue

            # 交代を引き起こしたアイテムを消費させる
            if flag.consume_item():
                self.add_turn_log(player, f"{self.active(player).item.name}消費")
                self.active(player).item.consume()

            # コマンドが予約されていなければ、プレイヤーの方策関数に従う
            if not self.state(player).reserved_commands:
                self.reserve_command(player, player.choose_switch_command(self))

            # 交代コマンドを取得
            command = self.state(player).reserved_commands.pop(0)

            self.run_switch(player, player.team[command.idx], emit=emit_on_each_switch)
            switched_players.append(player)

        # 全員の着地処理を同時に実行
        if not emit_on_each_switch:
            for mon in self.get_speed_order():
                player = self.find_player(mon)
                if player in switched_players:
                    ctx = EventContext(mon)
                    self.events.emit(Event.ON_SWITCH_IN, ctx=ctx)

    def run_faint_switch(self):
        '''
        while self.winner() is None:
            target_players = []
            if not self.has_interrupt():
                for player in self.players:
                    if self.active(player).hp == 0:
                        self.state(player).interrupt = Interrupt.FAINTED
                        target_players.append(player)

            # 交代を行うプレイヤーがいなければ終了
            if not target_players:
                return

            self.run_interrupt_switch(Interrupt.FAINTED, False)
        '''
        if self.winner():
            return

        # 交代フラグを設定
        if not self.has_interrupt():
            for player in self.players:
                if self.active(player).hp == 0:
                    self.state(player).interrupt = Interrupt.FAINTED

        # 交代を行うプレイヤー
        switch_players = [pl for pl, st in zip(self.players, self.states)
                          if st.interrupt == Interrupt.FAINTED]

        # 対象プレイヤーがいなければ終了
        if not switch_players:
            return

        # 交代
        self.run_interrupt_switch(Interrupt.FAINTED, False)

        # すべての死に出しが完了するまで再帰的に実行
        self.run_faint_switch()

    def advance_turn(self, commands: dict[Player, Command] | None = None):
        # 引数に指定されたコマンドを優先させる
        if commands:
            for player, command in commands.items():
                self.reserve_command(player, command)

        if not self.has_interrupt():
            self.init_turn()

        if self.turn == 0:
            if not self.has_interrupt():
                # ポケモンを選出
                self.run_selection()

                # ポケモンを場に出す
                self.run_initial_switch()

            # だっしゅつパックによる交代
            self.run_interrupt_switch(Interrupt.EJECTPACK_ON_START)

            return

        if not self.has_interrupt():
            # 予約されているコマンドがなければ、方策関数に従ってコマンドを予約する
            for player, state in zip(self.players, self.states):
                if not state.reserved_commands:
                    self.reserve_command(player, player.choose_action_command(self))

            # 行動前の処理
            self.events.emit(Event.ON_BEFORE_ACTION)

        # 交代
        for mon in self.get_speed_order():
            # 交代フラグ
            idx = self.actives.index(mon)
            interrupt = Interrupt.ejectpack_on_switch(idx)

            if not self.has_interrupt():
                state = self.states[idx]
                if state.reserved_commands[0].is_switch():
                    command = state.reserved_commands.pop(0)
                    player = self.find_player(mon)
                    new = player.team[command.idx]
                    self.run_switch(player, new)

                # だっしゅつパックによる割り込みフラグを更新
                self.override_interrupt(interrupt)

            # だっしゅつパックによる交代
            self.run_interrupt_switch(interrupt)

        # 行動前の処理
        self.events.emit(Event.ON_BEFORE_MOVE)

        # 技の使用
        for mon in self.get_action_order():
            player = self.find_player(mon)
            self.add_turn_log(player, self.active(player).name)

            if not self.has_interrupt():
                # 技の発動
                command = self.state(player).reserved_commands.pop(0)
                move = self.command_to_move(player, command)
                self.run_move(mon, move)

            # だっしゅつボタンによる交代
            self.run_interrupt_switch(Interrupt.EJECTBUTTON)

            # ききかいひによる交代
            self.run_interrupt_switch(Interrupt.EMERGENCY)

            # 交代技による交代
            self.run_interrupt_switch(Interrupt.PIVOT)

            interrupt = Interrupt.ejectpack_on_after_move(
                self.players.index(player))

            if not self.has_interrupt():
                # 交代技の後の処理
                self.events.emit(Event.ON_AFTER_PIVOT,
                                 ctx=EventContext(self.active(player)))

                # だっしゅつパックによる割り込みフラグを更新
                self.override_interrupt(interrupt)

            # だっしゅつパックによる交代
            self.run_interrupt_switch(interrupt)

        # ターン終了時の処理 (1)
        if not self.has_interrupt():
            self.events.emit(Event.ON_TURN_END_1)

        # ターン終了時の処理 (2)
        if not self.has_interrupt():
            self.events.emit(Event.ON_TURN_END_2)

        # ききかいひによる交代
        self.run_interrupt_switch(Interrupt.EMERGENCY)

        # ターン終了時の処理 (3)
        if not self.has_interrupt():
            self.events.emit(Event.ON_TURN_END_3)

        # ききかいひによる交代
        self.run_interrupt_switch(Interrupt.EMERGENCY)

        # ターン終了時の処理 (4)
        if not self.has_interrupt():
            self.events.emit(Event.ON_TURN_END_4)

        # ききかいひによる交代
        self.run_interrupt_switch(Interrupt.EMERGENCY)

        # ターン終了時の処理 (5)
        if not self.has_interrupt():
            self.events.emit(Event.ON_TURN_END_5)

            # だっしゅつパックによる割り込みフラグを更新
            self.override_interrupt(Interrupt.EJECTPACK_ON_TURN_END)

        # だっしゅつパックによる交代
        self.run_interrupt_switch(Interrupt.EJECTPACK_ON_TURN_END)

        # ターン終了時の処理 (5)
        if not self.has_interrupt():
            self.events.emit(Event.ON_TURN_END_6)

        self.run_interrupt_switch(Interrupt.EJECTPACK_ON_TURN_END)

        # 瀕死による交代
        self.run_faint_switch()
