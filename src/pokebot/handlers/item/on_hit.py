from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.core.events import EventContext
from .common import write_log_and_consume


def いのちのたま(battle: Battle, ctx: EventContext):
    if ctx.source.item == "いのちのたま" and \
            ctx.source.modify_hp(battle, -ctx.source.max_hp // 8):
        write_log_and_consume(battle, ctx.source)
