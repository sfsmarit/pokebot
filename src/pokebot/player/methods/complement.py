from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..random_player import RandomPlayer

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Phase, Command
from pokebot.core import PokeDB
from pokebot.core import Pokemon
from pokebot.core import Pokemon
from pokebot.core.ability import Ability
from pokebot.core.item import Item
from pokebot.core import Move
from pokebot.battle.battle import Battle


def _complement_opponent_selection(self: RandomPlayer, battle: Battle):
    """相手の選出情報を補完する"""
    opp = PlayerIndex(not self.idx)
    opponent = battle.player[opp]

    selection_indexes = battle.selection_indexes[opp]
    n = battle.n_selection

    # 選出の補完
    if len(selection_indexes) <= n:
        unobserved_indexes = [i for i in range(len(opponent.team)) if i not in selection_indexes]
        selection_indexes += unobserved_indexes[:n-len(selection_indexes)]

    # 技の補完
    for i in selection_indexes:
        p = opponent.team[i]
        if not p.moves:
            p.add_move('テラバースト')


def _complement_opponent_move(self: RandomPlayer, battle: Battle) -> Move:
    """相手の選択した技を補完する"""
    opp = PlayerIndex(not self.idx)
    available_commands = battle.available_commands(opp, phase=Phase.BATTLE)
    available_moves = [battle.pokemon[opp].moves[cmd.index] for cmd in available_commands if cmd.is_move]
    if not available_moves:
        # raise Exception("Empty move")
        available_moves = [Move("わるあがき")]
    return available_moves[0]


def _complement_opponent_switch(self: RandomPlayer, battle: Battle) -> Command:
    """相手の交代コマンドが開示されていない場合に補完する"""
    opp = PlayerIndex(not self.idx)
    return battle.available_commands(opp)[0]


def _complement_opponent_kata(poke: Pokemon,
                              kata: str,
                              overwrite_nature: bool,
                              overwrite_ability: bool,
                              overwrite_item: bool,
                              overwrite_terastal: bool,
                              overwrite_move: bool,
                              overwrite_effort: bool):
    """ポケモンの情報を補完する"""
    name = poke.name

    # 型データに登録されている名前に変換する
    if name in PokeDB.name_to_kata_name:
        name = PokeDB.name_to_kata_name[name]

    # 型データがあれば優先して参照し、なければポケモンHOMEの統計データを参照する
    if name in PokeDB.name_to_kata_list:
        # 指定された型が見つからなければ、最も数が多い型を参照する
        if kata not in PokeDB.kata_data:
            kata = list(PokeDB.name_to_kata_list[name].keys())[0]

        nature = poke.nature  # TODO 型データに性格を追加
        ability = Ability(list(PokeDB.kata_data[kata]['abilities'].keys())[0])
        item = Item(list(PokeDB.kata_data[kata]['items'].keys())[0])
        terastal = list(PokeDB.kata_data[kata]['terastals'].keys())[0]
        moves = PokeDB.kata_data[kata]['moves']
        effort = poke.effort  # TODO 型データに努力値を追加

    elif name in PokeDB.home:
        nature = PokeDB.home[name]['nature'][0]
        ability = Ability(PokeDB.home[name]['ability'][0])
        item = Item(PokeDB.home[name]['item'][0])
        terastal = PokeDB.home[name]['terastal'][0]
        moves = PokeDB.home[name]['move'][:4]
        effort = poke.effort  # 努力値の情報なし

    if overwrite_nature:
        poke.nature = nature

    if overwrite_ability and not poke.ability.observed:
        poke.ability = ability

    if overwrite_item and not poke.item.observed:
        poke.item = item

    if overwrite_terastal and not poke.terastal:
        poke.terastal = terastal

    if overwrite_move:
        for move in moves:
            if len(poke.moves) == 4:
                break
            poke.add_move(move)

    # if overwrite_effort:
    #    p.effort = effort
