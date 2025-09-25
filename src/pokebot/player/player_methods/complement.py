from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..player import Player

from pokebot.common.enums import Phase, Command
# from pokebot.common import PokeDB
from pokebot.pokedb import Pokemon, Ability, Item, Move
from pokebot.core.battle import Battle


def _complement_opponent_selection(self: Player, battle: Battle):
    """相手の選出情報を補完する"""
    opp = int(not self.idx)
    opponent = battle.players[opp]

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


def _complement_opponent_move(self: Player, battle: Battle) -> Move:
    """相手の選択した技を補完する"""
    opp = int(not self.idx)
    available_commands = battle.available_commands(opp, phase=Phase.ACTION)
    available_moves = [battle.pokemons[opp].moves[cmd.index] for cmd in available_commands if cmd.is_move]
    if not available_moves:
        # raise Exception("Empty move")
        available_moves = [Move("わるあがき")]
    return available_moves[0]


def _complement_opponent_switch(self: Player, battle: Battle) -> Command:
    """相手の交代コマンドが開示されていない場合に補完する"""
    opp = int(not self.idx)
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
    if name in PokeDB.valid_kata_name:
        name = PokeDB.valid_kata_name[name]

    # 型データがあれば優先して参照し、なければポケモンHOMEの統計データを参照する
    if name in PokeDB.name_to_kata_list:
        # 指定された型が見つからなければ、最も数が多い型を参照する
        if kata not in PokeDB.kata:
            kata = list(PokeDB.name_to_kata_list[name].keys())[0]

        nature = poke.nature
        ability = Ability(list(PokeDB.kata[kata]['abilities'].keys())[0])
        item = Item(list(PokeDB.kata[kata]['items'].keys())[0])
        terastal = list(PokeDB.kata[kata]['terastals'].keys())[0]
        moves = PokeDB.kata[kata]['moves']
        effort = poke.effort

    elif name in PokeDB.home:
        nature = PokeDB.home[name].natures[0]
        ability = Ability(PokeDB.home[name].abilities[0])
        item = Item(PokeDB.home[name].items[0])
        terastal = PokeDB.home[name].terastals[0]
        moves = PokeDB.home[name].moves[:4]
        effort = poke.effort

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
