from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from jpoke.core.battle import Battle

from jpoke.utils.enums import Stat
from jpoke.core.event import EventContext
from jpoke.handlers import HandlerOutput


def かちき(battle: Battle, value: Any, ctx: EventContext):
    if value < 0 and ctx.by_foe and \
            battle.modify_stat(ctx.source, Stat.C, +2):
        battle.add_turn_log(ctx.source, ctx.source.ability.name)
