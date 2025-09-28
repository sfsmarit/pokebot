from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.core.events import EventContext


def たべのこし(battle: Battle, ctx: EventContext):
    if ctx.source.item == "たべのこし" and \
            ctx.source.modify_hp(battle, ctx.source.max_hp // 16):
        battle.insert_turn_log(-1, ctx.source, ctx.source.item.name)
