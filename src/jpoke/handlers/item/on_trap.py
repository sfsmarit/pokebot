from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from jpoke.core.battle import Battle

from jpoke.core.event import EventContext
from .common import write_log_and_consume


def きれいなぬけがら(battle: Battle, value: Any, ctx: EventContext):
    ctx.source.field_status._trapped = False
