from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.core.events import EventContext
from .common import write_log_and_consume


def たべのこし(battle: Battle, ctx: EventContext):
    if ctx.source.item == "たべのこし" and \
            battle.modify_hp(ctx.source, ctx.source.max_hp // 16):
        write_log_and_consume(battle, ctx.source)
