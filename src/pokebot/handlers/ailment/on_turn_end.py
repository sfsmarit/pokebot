from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pokebot.core.battle import Battle
    from pokebot.core.events import EventContext

from pokebot.handlers import common


def どく(battle: Battle, value: Any, ctx: EventContext):
    if battle.modify_hp(ctx.source, r=-1/8):
        battle.add_turn_log(ctx.source, "どくダメージ")


def もうどく(battle: Battle, value: Any, ctx: EventContext):
    ctx.source.ailment.count += 1
    r = max(-1, -ctx.source.ailment.count/16)
    if battle.modify_hp(ctx.source, r=r):
        battle.add_turn_log(ctx.source, "もうどくダメージ")
