from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.core.events import EventContext
from .common import write_log_and_consume


def きれいなぬけがら(battle: Battle, ctx: EventContext):
    ctx.source.field_status._trapped &= (
        ctx.source.item != "きれいなぬけがら"
    )
