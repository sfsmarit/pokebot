from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pokebot.core.battle import Battle

from pokebot.utils.enums import Stat
from pokebot.core.events import EventContext
from pokebot.handlers import common


def いかく(battle: Battle, value: Any, ctx: EventContext):
    if battle.modify_stat(battle.foe(ctx.source), Stat.A, -1, by_foe=True):
        battle.add_turn_log(ctx.source, ctx.source.ability.name)


def きんちょうかん(battle: Battle, value: Any, ctx: EventContext):
    battle.foe(ctx.source).field_status.nervous = True
    battle.add_turn_log(ctx.source, ctx.source.ability.name)


def グラスメイカー(battle: Battle, value: Any, ctx: EventContext):
    common.activate_terrain(battle, ctx, "グラスフィールド")


def ぜったいねむり(battle: Battle, value: Any, ctx: EventContext):
    if ctx.source.ailment.overwrite(battle.events, "ねむり"):
        battle.add_turn_log(ctx.source, ctx.source.ability.name)
