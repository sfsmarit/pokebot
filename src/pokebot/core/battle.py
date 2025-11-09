import time
from random import Random
from typing import Self
from copy import deepcopy
import json

from pokebot.utils import copy_utils as ut
from pokebot.utils.enums import Command, Stat

from pokebot.player.player import Player

from .events import Event, Interrupt, EventManager, EventContext
from .player_state import PlayerState
from .logger import Logger
from .pokedb import PokeDB
from .pokemon import Pokemon
from .move import Move

from .damage import DamageCalculator, DamageContext


class Battle:
    def __init__(self,
                 players: list[Player],
                 seed: int | None = None) -> None:

        if seed is None:
            seed = int(time.time())

        self.seed: int = seed
        self.turn: int = -1
        self._winner: Player | None = None

        self.states: dict[Player, PlayerState] = \
            {player: PlayerState() for player in players}

        self.random = Random(self.seed)
        self.events = EventManager(self)
        self.logger = Logger()
        self.damage_calculator: DamageCalculator = DamageCalculator(self.events)

        if seed is not None:
            self.seed = seed

    def export_log(self, filepath):
        """
        試合のログを書き出す

        Parameters
        ----------
        filepath :
            json 形式のファイルパス
        """
        data = {
            "seed": self.seed,
            "players": [],
        }

        for player, state in self.states.items():
            data["players"].append({
                "name": player.name,
                "selection_indexes": state.selected_idxes,
                "commands": {},
                "team": [poke.dump() for poke in player.team],
            })

        for log in self.logger.command_logs:
            data["players"][log.player_idx]["commands"].setdefault(
                str(log.turn), []).append(log.command.name)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2))

    @classmethod
    def reconstruct_from_log(cls, filepath) -> Self:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        new = cls(
            [Player(), Player()],
            seed=data["seed"],
        )

        for i, (player, state) in enumerate(new.states.items()):
            player_data = data["players"][i]
            player.name = player_data["name"]
            state.selected_idxes = player_data["selection_indexes"]

            for p in player_data["team"]:
                poke = PokeDB.reconstruct_pokemon_from_log(p)
                player.team.append(poke)

            for t, command_names in player_data["commands"].items():
                for s in command_names:
                    command = Command[s]
                    new.reserve_command(player, command, turn=int(t))

        return new

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.fast_copy(self, new, keys_to_deepcopy=[
            "states", "random", "events", "logger", "damage_calculator",
        ])

        # 参照を複製したインスタンスに置き換える
        new.events.battle = new
        new.damage_calculator.events = new.events

        # 複製した EventManager.handlers[event][handler]: list[Pokemon | None] の
        # 参照先を複製した後のポケモンに置き換える
        for event, data in new.events.handlers.items():
            for handler, pokes in data.items():
                new_pokes = []
                for p in pokes:
                    if isinstance(p, Pokemon):
                        player = self.find_player(p)
                        player_idx = self.players.index(player)
                        team_idx = player.team.index(p)
                        new_pokes.append(new.players[player_idx].team[team_idx])
                    else:
                        new_pokes.append(p)
                new.events.handlers[event][handler] = new_pokes

        # 乱数の隠蔽
        new.random.seed(int(time.time()))

        return new

    def masked(self, perspective: Player) -> tuple[Self, Player]:
        # TODO mask
        new = deepcopy(self)
        new_player = new.players[self.players.index(perspective)]
        return new, new_player

    @property
    def players(self):
        return list(self.states.keys())

    def active(self, player: Player) -> Pokemon:
        if (i := self.states[player].active_idx) is not None:
            return player.team[i]
        else:
            return None  # type: ignore

    def selected(self, player: Player) -> list[Pokemon]:
        return [player.team[i] for i in self.states[player].selected_idxes]

    def init_turn(self):
        for state in self.states.values():
            state.turn_reset()
        self.turn += 1

    def find_player(self, poke: Pokemon) -> Player:
        for player in self.players:
            if poke in player.team:
                return player
        raise Exception("Player not found.")

    def team_idx(self, poke: Pokemon) -> int:
        player = self.find_player(poke)
        return player.team.index(poke)

    def foe(self, active: Pokemon) -> Pokemon:
        actives = [self.active(pl) for pl in self.players]
        return actives[not actives.index(active)]

    def rival(self, player: Player) -> Player:
        return self.players[not self.players.index(player)]

    def can_use_terastal(self, player: Player) -> bool:
        return all(poke.can_terastallize() for poke in self.selected(player))

    def get_available_selection_commands(self, player: Player) -> list[Command]:
        return Command.selection_commands()[:len(player.team)]

    def get_available_switch_commands(self, player: Player) -> list[Command]:
        return [cmd for poke, cmd in zip(player.team, Command.switch_commands())
                if poke in self.selected(player) and
                poke is not self.active(player)]

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
        self.states[player].reserved_commands.append(command)
        idx = self.players.index(player)
        self.logger.add_command_log(self.turn, idx, command)

    def get_turn_logs(self, turn: int | None = None) -> dict[Player, list[str]]:
        if turn is None:
            turn = self.turn
        return {pl: self.logger.get_turn_logs(turn, i) for i, pl in enumerate(self.players)}

    def add_turn_log(self, source: Player | list[Player] | Pokemon, text: str):
        if isinstance(source, Player):
            idxes = [self.players.index(source)]
        elif isinstance(source, list):
            idxes = [self.players.index(pl) for pl in source]
        elif isinstance(source, Pokemon):
            idxes = [self.players.index(self.find_player(source))]

        for idx in idxes:
            self.logger.add_turn_log(self.turn, idx, text)

    def get_speed_order(self) -> list[Player]:
        # TODO get_speed_order
        return self.players

    def get_action_order(self) -> list[Player]:
        # TODO get_action_order
        return self.players

    def TOD_score(self, player: Player, alpha: float = 1):
        n_alive, total_max_hp, total_hp = 0, 0, 0
        for poke in self.selected(player):
            total_max_hp += poke.max_hp
            total_hp += poke.hp
            if poke.hp:
                n_alive += 1
        return n_alive + alpha * total_hp / total_max_hp

    def winner(self) -> Player | None:
        if not self._winner:
            TOD_scores = [self.TOD_score(pl) for pl in self.players]
            if 0 in TOD_scores:
                idx = TOD_scores.index(0)
                self._winner = self.players[not idx]
                self.add_turn_log(self._winner, "勝ち")
                self.add_turn_log(self.players[idx], "負け")
        return self._winner

    def run_selection(self):
        for player, state in self.states.items():
            if not state.selected_idxes:
                commands = player.choose_selection_commands(self)
                state.selected_idxes = [c.idx for c in commands]

    def run_move(self, player: Player, move: Move):
        source = self.active(player)
        foe = self.foe(source)

        # 技のハンドラを登録
        move.register_handlers(self.events, source)

        self.add_turn_log(player, f"{move.name}")

        # 行動成功判定
        self.events.emit(Event.ON_TRY_ACTION, ctx=EventContext(source))

        # 発動成功判定
        self.events.emit(Event.ON_TRY_MOVE, ctx=EventContext(source))

        source.field_status.executed_move = move

        # TODO 命中判定
        pass

        # 無効判定
        self.events.emit(Event.ON_TRY_IMMUNE, ctx=EventContext(source))

        # ダメージ計算
        damage = self.calc_damage(source, move)

        if False:
            # TODO みがわり被弾処理
            self.events.emit(Event.ON_HIT, ctx=EventContext(source))

        else:
            # HPコストの支払い
            self.events.emit(Event.ON_PAY_HP, ctx=EventContext(source))

            # ダメージ修正
            damage = self.events.emit(Event.ON_MODIFY_DAMAGE, value=damage, ctx=EventContext(source))

            if damage:
                # ダメージ付与
                self.modify_hp(foe, -damage)

                # ダメージを与えたときの処理
                self.events.emit(Event.ON_HIT, ctx=EventContext(source))
                self.events.emit(Event.ON_DAMAGE, ctx=EventContext(source))

        move.unregister_handlers(self.events, source)

    def get_move_from_command(self, player: Player, command: Command) -> Move:
        if command == Command.STRUGGLE:
            return PokeDB.create_move("わるあがき")
        elif command.is_zmove():
            return PokeDB.create_move("わるあがき")
        else:
            return self.active(player).moves[command.idx]

    def modify_hp(self, target: Pokemon, v: int) -> bool:
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
        return self.damage_calculator.single_hit_damages(
            attacker, defender, move, ctx)

    def has_interrupt(self) -> bool:
        return any(x.interrupt != Interrupt.NONE for x in self.states.values())

    def override_interrupt(self, flag: Interrupt, only_first: bool = True):
        for player in self.get_speed_order():
            if self.states[player].interrupt == Interrupt.REQUESTED:
                self.states[player].interrupt = flag
                if only_first:
                    return

    def run_switch(self, player: Player, new: Pokemon, emit: bool = True):
        # 割り込みフラグを破棄
        self.states[player].interrupt = Interrupt.NONE

        # 退場
        old = self.active(player)
        if old is not None:
            self.events.emit(Event.ON_SWITCH_OUT, ctx=EventContext(old))
            old.switch_out(self.events)
            self.add_turn_log(player, f"{old.name} {'交代' if old.hp else '瀕死'}")

        # 入場
        self.states[player].active_idx = player.team.index(new)
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
        self.states[player].already_switched = True

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
            if self.states[player].interrupt != flag:
                continue

            # 交代を引き起こしたアイテムを消費させる
            if flag.consume_item():
                self.add_turn_log(player, f"{self.active(player).item.name}消費")
                self.active(player).item.consume()

            # コマンドが予約されていなければ、プレイヤーの方策関数に従う
            if not self.states[player].reserved_commands:
                self.reserve_command(player, player.choose_switch_command(self))

            # 交代コマンドを取得
            command = self.states[player].reserved_commands.pop(0)

            self.run_switch(player, player.team[command.idx], emit=emit_on_each_switch)
            switched_players.append(player)

        # 全員の着地処理を同時に実行
        if not emit_on_each_switch:
            for player in self.get_speed_order():
                if player in switched_players:
                    self.events.emit(Event.ON_SWITCH_IN,
                                     ctx=EventContext(self.active(player)))

    def run_faint_switch(self):
        '''
        while self.winner() is None:
            target_players = []
            if not self.has_interrupt():
                for player in self.players:
                    if self.active(player).hp == 0:
                        self.states[player].interrupt = Interrupt.FAINTED
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
                    self.states[player].interrupt = Interrupt.FAINTED

        # 交代を行うプレイヤー
        switch_players = [pl for pl, st in self.states.items()
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
            # コマンドが予約されていなければ、プレイヤーの方策関数に従う
            for player, state in self.states.items():
                if not state.reserved_commands:
                    self.reserve_command(player, player.choose_action_command(self))

            # 行動前の処理
            self.events.emit(Event.ON_BEFORE_ACTION)

        # 行動: 交代
        for player in self.get_action_order():
            # 交代フラグ
            idx = self.players.index(player)
            interrupt = Interrupt.ejectpack_on_switch(idx)

            if not self.has_interrupt():
                if self.states[player].reserved_commands[0].is_switch():
                    command = self.states[player].reserved_commands.pop(0)
                    new = player.team[command.idx]
                    self.run_switch(player, new)
                else:
                    self.add_turn_log(player, self.active(player).name)

                # だっしゅつパックによる割り込みフラグを更新
                self.override_interrupt(interrupt)

            # だっしゅつパックによる交代
            self.run_interrupt_switch(interrupt)

        # 行動前の処理
        self.events.emit(Event.ON_BEFORE_MOVE)

        # 行動順の決定
        action_order = self.get_action_order()

        # 行動: 技
        for player in action_order:
            # このターンに交代済みなら行動不可
            if self.states[player].already_switched:
                continue

            if not self.has_interrupt():
                command = self.states[player].reserved_commands.pop(0)
                move = self.get_move_from_command(player, command)

                # 技の発動
                self.run_move(player, move)

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

        # ききかいひによる交代
        self.run_interrupt_switch(Interrupt.EMERGENCY)

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

            # だっしゅつパックによる割り込みフラグを更新
            self.override_interrupt(Interrupt.EJECTPACK_ON_TURN_END)

        # だっしゅつパックによる交代
        self.run_interrupt_switch(Interrupt.EJECTPACK_ON_TURN_END)

        # ターン終了時の処理 (5)
        if not self.has_interrupt():
            self.events.emit(Event.ON_TURN_END_5)

        self.run_interrupt_switch(Interrupt.EJECTPACK_ON_TURN_END)

        # 瀕死による交代
        self.run_faint_switch()
