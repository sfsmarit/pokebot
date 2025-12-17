from pokebot.core.event import Event, Handler
from .models import AilmentData
from pokebot.handlers.ailment import on_turn_end


AILMENTS: dict[str, AilmentData] = {
    "": AilmentData(),
    "どく": AilmentData(
        handlers={
            Event.ON_TURN_END_4: Handler(on_turn_end.どく),
        },
    ),
    "もうどく": AilmentData(
        handlers={
            Event.ON_TURN_END_4: Handler(on_turn_end.もうどく),
        },
    ),
}
