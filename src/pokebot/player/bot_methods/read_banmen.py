from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot_player import BotPlayer

import warnings

from pokebot.common.enums import Time
from pokebot.common import PokeDB
from pokebot.model import Pokemon, Item


def _read_banmen(self: BotPlayer) -> bool:
    type(self).press_button('Y', post_sleep=Time.TRANSITION_CAPTURE.value)

    # 相手にテラスタル権があればテラスタイプを確認
    if self.battle.can_terastallize(1):
        opp_terastal = self._read_opponent_terastal()
    else:
        opp_terastal = ""

    # 自分の盤面を取得
    if 'player0' not in self.recognized_labels:
        print('自分の盤面')
        type(self).press_button('A', post_sleep=Time.TRANSITION_CAPTURE.value+0.5)

        if not self._is_condition_window():
            warnings.warn('Invalid screen')
            return False

        # 場のポケモンを取得
        label = self._read_active_label(0, capture=False)

        # 場のポケモンの修正
        if not self.battle.pokemons[0] or label != self.battle.pokemons[0].label:
            poke = Pokemon.find(self.team, label=label)
            self.battle.turn_mgr.switch_pokemon(0, switch=poke, landing=False)

        # ポケモンの状態の修正
        self.battle.pokemons[0].hp = max(1, min(self._read_hp(capture=False), self.battle.pokemons[0].stats[0]))
        self.battle.pokemons[0].ailment = self._read_ailment(capture=False)
        self.battle.poke_mgrs[0].rank[1:] = self._read_rank(capture=False)
        self._overwrite_condition(0, self._read_condition(capture=False))

        # アイテムの修正
        if (item := self._read_item(capture=False)) != self.battle.pokemons[0].item:
            if item:
                self.battle.pokemons[0].item = Item(item)
                print(f"\tアイテム {self.battle.pokemons[0].item}")
            else:
                self.battle.pokemons[0].item.active = False
                print(f"\t失ったアイテム {self.battle.pokemons[0].item.name_lost}")

            self.battle.poke_mgrs[0].choice_locked = False  # アイテム変化 = こだわり解除
            self.battle.pokemons[0].item.observed = True  # 観測

        self.recognized_labels.append('player0')  # 認識完了

    else:
        type(self).press_button('A', post_sleep=0.2)

    # 相手の盤面を取得
    opponent_switched = False

    if not 'player1' in self.recognized_labels:
        print('相手の盤面')
        type(self).press_button('R', post_sleep=Time.TRANSITION_CAPTURE.value)

        if not self._is_condition_window():
            warnings.warn('Invalid screen')
            return False

        # 場のポケモンを取得
        label = self._read_active_label(1, capture=False)

        if not self.online:
            # オフライン対戦では、対面している相手ポケモン = 相手の全選出 とみなす
            name = PokeDB.label_to_names[label][0]
            self.battle.pokemons[1] = Pokemon(name)
            self.battle.pokemons[1].level = 80
            self.battle.pokemons[1].observed = True  # 観測
            self.battle.players[1].team = [self.battle.pokemons[1]]
            self.battle.selection_indexes[1] = [0]

        elif not self.battle.pokemons[1] or label != self.battle.pokemons[1].label:
            opponent_switched = True

            # 初見なら相手選出に追加
            if label not in [p.label for p in self.battle.selected_pokemons(1)]:
                switch_idx = Pokemon.index(self.battle.players[1].team, label=label)
                self.battle.turn_mgr.switch_pokemon(1, switch_idx=switch_idx, landing=False)
                # フォルムを識別
                if (name := self._read_form(label, capture=False)):
                    self.battle.pokemons[1].name = name
                print(f"\t選出 {[p.name for p in self.battle.selected_pokemons(1)]}")

        # 相手のテラスタルを取得
        if opp_terastal:
            self.battle.pokemons[1].terastal = opp_terastal
            self.battle.pokemons[1].terastallize()

        self.battle.pokemons[1].hp_ratio = self._read_hp_ratio(capture=False)
        self.battle.pokemons[1].ailment = self._read_ailment(capture=False)
        self.battle.poke_mgrs[1].rank[1:] = self._read_rank(capture=False)
        self._overwrite_condition(1, self._read_condition(capture=False))
        self.recognized_labels.append('player1')  # 認識完了

    # コマンド選択画面に戻る
    while True:
        type(self).press_button('B', n=5, post_sleep=Time.TRANSITION_CAPTURE.value)
        if self._is_action_window():
            break

    # 相手が交代済みなら控えが瀕死か確認
    if opponent_switched:
        type(self).press_button('PLUS', post_sleep=Time.TRANSITION_CAPTURE.value)
        self._read_fainting_opponent()
        type(self).press_button('B', post_sleep=0.2)

    return True
