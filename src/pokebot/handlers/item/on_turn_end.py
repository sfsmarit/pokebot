from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.core.events import EventContext
from .common import write_log_and_consume


def たべのこし(battle: Battle, value: Any, ctx: EventContext):
    if battle.modify_hp(ctx.source, ctx.source.max_hp // 16):
        write_log_and_consume(battle, ctx.source)
