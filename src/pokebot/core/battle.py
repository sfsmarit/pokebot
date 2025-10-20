import time
from random import Random

from pokebot.common import utils as ut
from pokebot.common.enums import Command, Stat
from pokebot.logger import Logger, TurnLog, CommandLog

from pokebot.player.player import Player

from .events import Event, Interrupt, EventManager, EventContext
from .player_state import PlayerState
from .pokedb import PokeDB
from .pokemon import Pokemon
from .move import Move

from .damage import DamageCalculator, DamageContext


class Battle:
    def __init__(self,
                 players: list[Player],
                 seed: int | None = None) -> None:

        self.states: dict[Player, PlayerState] = \
            {player: PlayerState() for player in players}

        self.seed = seed if seed is not None else int(time.time())

        self.turn: int = -1
        self._winner: Player | None = None

        self.random = Random(seed)
        self.events = EventManager(self)
        self.logger = Logger()
        self.damage_calculator: DamageCalculator = DamageCalculator(self.events)

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        ut.fast_copy(self, new, keys_to_deepcopy=[
            "states", "random", "events", "logger", "damage_calculator",
        ])

        # 参照をコピーに移し替える
        new.events.battle = new
        new.damage_calculator.events = new.events

        # 乱数の隠蔽
        new.random.seed(int(time.time()))

        return new

    @property
    def players(self):
        return list(self.states.keys())

    def active(self, player: Player) -> Pokemon:
        return player.team[self.states[player].active_idx]

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

    def foe(self, active: Pokemon) -> Pokemon:
        actives = [self.active(pl) for pl in self.players]
        return actives[(actives.index(active)+1) % 2]

    def rival(self, player: Player) -> Player:
        return self.players[(self.players.index(player)+1) % 2]

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

    def get_turn_logs(self, turn: int | None = None) -> dict[Player, list[str]]:
        if turn is None:
            turn = self.turn
        return self.logger.get_turn_logs(turn)

    def add_turn_log(self, obj: Player | list[Player] | Pokemon, text: str):
        if isinstance(obj, Player):
            obj = [obj]
        elif isinstance(obj, Pokemon):
            obj = [self.find_player(obj)]
        self.logger.append(TurnLog(self.turn, obj, text))

    def get_speed_order(self) -> list[Player]:
        # TODO
        return self.players

    def get_action_order(self) -> list[Player]:
        # TODO
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
        for player in self.players:
            commands = player.choose_selection_commands(self)
            self.states[player].selected_idxes = [c.idx for c in commands]

    def run_move(self, player: Player, move: Move):
        source = self.active(player)
        foe = self.foe(source)

        # 技のハンドラを登録
        move.register_handlers(self.events, source)

        # 技判定より前の処理
        self.events.emit(Event.ON_BEFORE_MOVE, ctx=EventContext(source))

        self.add_turn_log(player, f"{move.name}")

        # 発動成功判定
        self.events.emit(Event.ON_TRY_MOVE, ctx=EventContext(source))

        # 命中判定
        pass

        source.field_status.executed_move = move

        # ダメージ計算
        damage = self.calc_damage(source, move)

        # ダメージ付与
        self.modify_hp(foe, -damage)

        # 技が命中したときの処理
        self.events.emit(Event.ON_HIT, ctx=EventContext(source))

        # 技によってダメージを与えたときの処理
        if damage:
            self.events.emit(Event.ON_DAMAGE, ctx=EventContext(source))

        move.unregister_handlers(self.events, source)

    def query_switch(self, player: Player) -> Pokemon:
        if (x := self.states[player].scheduled_switch_commands):
            command = x.pop(0)
        else:
            command = player.choose_switch_command(self)
        return player.team[command.idx]

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
                    self_harm: bool = False) -> int:
        return self.random.choice(
            self.calc_damages(attacker, move, critical, self_harm))

    def calc_damages(self,
                     attacker: Pokemon,
                     move: Move | str,
                     critical: bool = False,
                     self_harm: bool = False) -> list[int]:
        if isinstance(move, str):
            move = PokeDB.create_move(move)
        defender = attacker if self_harm else self.foe(attacker)
        dmg_ctx = DamageContext(critical, self_harm)
        return self.damage_calculator.single_hit_damages(
            attacker, defender, move, dmg_ctx)

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
        # 交代
        target_players = []
        for player in self.players:
            if self.states[player].interrupt != flag:
                continue

            # アイテム消費
            if flag.by_consumable_item():
                self.add_turn_log(player, f"{self.active(player).item.name}消費")
                self.active(player).item.consume()

            self.run_switch(player, self.query_switch(player), emit=emit_on_each_switch)
            target_players.append(player)

        # 着地処理が完了していたら中断
        if not emit_on_each_switch:
            return

        # 交代したプレイヤーの着地処理をまとめて実行
        for player in self.get_speed_order():
            if player in target_players:
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

    def advance_turn(self, commands: dict[Player, Command] = {}):
        if not self.has_interrupt():
            self.init_turn()

        if self.turn == 0:
            if not self.has_interrupt():
                # ポケモンを選出
                self.run_selection()

                # ポケモンを場に出す
                self.run_initial_switch()

            # 割り込み
            self.run_interrupt_switch(Interrupt.EJECTPACK_ON_START)

            return

        if not self.has_interrupt():
            # 行動選択
            for player, state in self.states.items():
                if player in commands:
                    # 引数のコマンドを優先
                    state.command = commands[player]
                else:
                    # プレイヤーの方策関数に従う
                    state.command = player.choose_action_command(self)

            # 行動前の処理
            self.events.emit(Event.ON_BEFORE_ACTION)

        # 行動: 交代
        for player in self.get_action_order():
            # 交代フラグ
            idx = self.players.index(player)
            interrupt = Interrupt.ejectpack_on_switch(idx)

            if not self.has_interrupt():
                if (cmd := self.states[player].command).is_switch():
                    new = player.team[cmd.idx]
                    self.run_switch(player, new)
                else:
                    self.add_turn_log(player, self.active(player).name)

                # だっしゅつパックによる割り込みフラグを更新
                self.override_interrupt(interrupt)

            # だっしゅつパックによる交代
            self.run_interrupt_switch(interrupt)

        # 行動: 技
        for player in self.get_action_order():
            # このターンに交代済みなら行動不可
            if self.states[player].already_switched:
                continue

            # 技の発動
            move = self.get_move_from_command(player, self.states[player].command)
            self.run_move(player, move)

            # だっしゅつボタンによる交代
            self.run_interrupt_switch(Interrupt.EJECTBUTTON)

            # 交代技による交代
            self.run_interrupt_switch(Interrupt.PIVOT)

            # 交代フラグ
            idx = self.players.index(player)
            interrupt = Interrupt.ejectpack_on_after_move(idx)

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

        # ターン終了時の処理 (3)
        if not self.has_interrupt():
            self.events.emit(Event.ON_TURN_END_3)

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
