from pokebot.core.events import Event, Handler
from .registry import FieldData
from pokebot.handlers.global_field import on_turn_end


FIELDS: dict[str, FieldData] = {
    "": FieldData(),
    # Global fields
    "はれ": FieldData(
        turn_extension_item="あついいわ",
        handlers={
            Event.ON_TURN_END_1: Handler(on_turn_end.reduce_weather_count),
        },
    ),
    "すなあらし": FieldData(
        turn_extension_item="さらさらいわ",
        handlers={
            Event.ON_TURN_END_1: Handler(on_turn_end.reduce_weather_count),
            Event.ON_TURN_END_2: Handler(on_turn_end.すなあらし),
        },
    ),
    "グラスフィールド": FieldData(
        turn_extension_item="グランドコート",
        handlers={
            Event.ON_TURN_END_3: Handler(on_turn_end.グラスフィールド),
            Event.ON_TURN_END_5: Handler(on_turn_end.reduce_terrain_count),
        },
    ),
    "じゅうりょく": FieldData(
        handlers={
        },
    ),
    "トリックルーム": FieldData(
        handlers={
        },
    ),
    # Side fields
    "リフレクター": FieldData(
        handlers={
        },
    ),
}
