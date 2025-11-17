from pokebot.core.events import Event, Handler
from .registry import AilmentData


AILMENTS: dict[str, AilmentData] = {
    "": AilmentData(),
    "どく": AilmentData(
        handlers={
        },
    ),

}
