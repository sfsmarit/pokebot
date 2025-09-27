from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import Bot

from pokebot.common.enums import Time, Phase, Command


def _input_selection_command(self: Bot, commands: list[Command]) -> list[int]:
    """選出コマンドを入力する"""
    indexes = [cmd.idx for cmd in commands]

    for team_idx in indexes + [6]:
        while True:
            pos = self.selection_cursor_position()
            if pos == team_idx:
                break

            if team_idx < len(self.team):
                n = team_idx - pos
            else:
                n = len(self.team) - pos
            button = 'DPAD_DOWN' if n > 0 else 'DPAD_UP'
            type(self).press_button(button, n=abs(n), post_sleep=Time.CAPTURE.value+0.1)

            # 入力が間に合わなかった場合、先頭のn匹を選出する
            if self.read_phase() != Phase.SELECTION:
                print('Failed to input commands')
                indexes = list(range(3))
                return indexes

        type(self).press_button('A', n=2, interval=0.2)

    return indexes


def _input_move_command(self: Bot, command: Command) -> bool:
    pp_list = []

    # 技選択画面に移動
    while True:
        if (pos := self.action_cursor_position()) == 0:
            break
        type(self).press_button('DPAD_UP', n=pos, post_sleep=Time.CAPTURE.value)

    type(self).press_button('A', post_sleep=1)

    # PPを取得
    for i in range(4):
        pp = self.read_pp(move_idx=i, capture=(i == 0))
        if pp == 0:
            # PPが0なら再度読み取る
            pp = self.read_pp(move_idx=i, capture=True)
        self.battle.pokemons[0].moves[i].pp = pp

    # PPがなければ中断
    if self.battle.pokemons[0].moves[command.idx] == 0:
        print(f"PP is zero")
        return False

    # テラスタル
    if command.is_terastal:
        type(self).press_button('R')

    # 技を入力
    while True:
        pos = self.move_cursor_position()
        if pos == command.idx:
            break
        delta = command.idx - pos
        button = 'DPAD_DOWN' if delta > 0 else 'DPAD_UP'
        type(self).press_button(button, n=abs(delta), post_sleep=Time.CAPTURE.value)
        if self.read_phase() != Phase.ACTION:
            break

    type(self).press_button('A')
    return True


def _input_switch_command(self: Bot, command: Command) -> bool:
    """交代コマンドを入力する"""
    type(self).press_button('DPAD_DOWN', post_sleep=Time.CAPTURE.value + 0.2)

    for i in range(len(self.team)-2):
        if self._read_switch_state() == 'alive' and \
                self._read_switch_label(i+1) == self.team[command.idx].label:
            break

        type(self).press_button('DPAD_DOWN', post_sleep=Time.CAPTURE.value + 0.1)

        if self.read_phase() != Phase.SWITCH:
            print('Invalid screen')
            return False

    type(self).press_button('A', n=2, interval=0.2)
    return True
