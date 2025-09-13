from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..pokemon_manager import ActivePokemonManager

import pokebot.common.utils as ut
from pokebot.common.enums import Ailment, SideField, Weather, Terrain


def _effective_speed(self: ActivePokemonManager, masked: bool) -> int:
    """場のポケモンまたは{p}の素早さ実効値を返す"""
    poke = self.pokemon
    if masked:
        poke = poke.masked()

    speed = int(poke.stats[5]*self.rank_modifier(5))

    if self.boosted_idx == 5:
        speed = int(speed*1.5)

    r = 4096

    match poke.ability.name:
        case 'かるわざ':
            if poke.ability.count:
                r = ut.round_half_up(r*2)
        case 'サーフテール':
            if self.battle.field_mgr.terrain() == Terrain.ELEC:
                r = ut.round_half_up(r*2)
        case 'すいすい':
            if self.battle.field_mgr.weather(self.idx) == Weather.RAINY:
                r = ut.round_half_up(r*2)
        case 'すなかき':
            if self.battle.field_mgr.weather() == Weather.SAND:
                r = ut.round_half_up(r*2)
        case 'スロースタート':
            r = ut.round_half_up(r*0.5)
        case 'はやあし':
            if poke.ailment:
                r = ut.round_half_up(r*1.5)
        case 'ゆきかき':
            if self.battle.field_mgr.weather() == Weather.SNOW:
                r = ut.round_half_up(r*2)
        case 'ようりょくそ':
            if self.battle.field_mgr.weather(self.idx) == Weather.SUNNY:
                r = ut.round_half_up(r*2)

    match poke.item.name:
        case 'くろいてっきゅう':
            r = ut.round_half_up(r*0.5)
        case 'こだわりスカーフ':
            r = ut.round_half_up(r*1.5)

    if self.battle.field_mgr.count[SideField.OIKAZE][self.idx]:
        r = ut.round_half_up(r*2)

    speed = ut.round_half_down(speed*r/4096)

    if poke.ailment == Ailment.PAR and poke.ability.name != 'はやあし':
        speed = int(speed*0.5)

    return speed
