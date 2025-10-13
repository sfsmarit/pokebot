from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..battle import Battle
    from pokebot.core.move import Move

from pokebot.common.enums import Command
from pokebot.core.events import Event, EventContext
from pokebot.core.pokedb import PokeDB


def run_move(self: Battle, player_idx: int, move: Move):
    source = self.actives[player_idx]
    foe = self.foe(source)

    move.register_handlers(self.events)

    # 技判定より前の処理
    self.events.emit(Event.ON_BEFORE_MOVE, EventContext(source))

    self.add_turn_log(self.get_player_index(source), f"{move}")

    # 発動成功判定
    self.events.emit(Event.ON_TRY_MOVE, EventContext(source))

    # 命中判定
    pass

    source.field_status.executed_move = move

    # ダメージ計算
    damage = self.calc_damage(source, move)

    # ダメージ付与
    self.modify_hp(foe, -damage)

    # 技が命中したときの処理
    self.events.emit(Event.ON_HIT, EventContext(source))

    # 技によってダメージを与えたときの処理
    if damage:
        self.events.emit(Event.ON_DAMAGE, EventContext(source))

    move.unregister_handlers(self.events)
