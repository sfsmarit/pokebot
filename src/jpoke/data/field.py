from jpoke.core.event import Event, Handler
from .models import FieldData
from jpoke.handlers import common, field as hdl


FIELDS: dict[str, FieldData] = {
    "": FieldData(),

    # Global fields
    "はれ": FieldData(
        turn_extension_item="あついいわ",
        handlers={
            Event.ON_TURN_END_1: Handler(
                lambda btl, val, ctx: hdl.reduce_global_field_count(btl, val, ctx, "weather"),
            ),
        },
    ),
    "あめ": FieldData(
        turn_extension_item="しめったいわ",
        handlers={
            Event.ON_TURN_END_1: Handler(
                lambda btl, val, ctx: hdl.reduce_global_field_count(btl, val, ctx, "weather"),
            ),
        },
    ),
    "すなあらし": FieldData(
        turn_extension_item="さらさらいわ",
        handlers={
            Event.ON_TURN_END_1: Handler(
                lambda btl, val, ctx: hdl.reduce_global_field_count(btl, val, ctx, "weather"),
            ),
            Event.ON_TURN_END_2: Handler(
                lambda btl, val, ctx: common.modify_hp(btl, val, ctx, "self", r=-1/16, log="すなあらし"),
            )
        },
    ),
    "ゆき": FieldData(
        turn_extension_item="つめたいいわ",
        handlers={
            Event.ON_TURN_END_1: Handler(
                lambda btl, val, ctx: hdl.reduce_global_field_count(btl, val, ctx, "weather"),
            ),
        },
    ),
    "エレキフィールド": FieldData(
        turn_extension_item="グランドコート",
        handlers={
            Event.ON_TURN_END_5: Handler(
                lambda btl, val, ctx: hdl.reduce_global_field_count(btl, val, ctx, "terrain"),
            )
        },
    ),
    "グラスフィールド": FieldData(
        turn_extension_item="グランドコート",
        handlers={
            Event.ON_TURN_END_3: Handler(
                lambda btl, val, ctx: common.modify_hp(btl, val, ctx, "self", r=1/16, log="グラスフィールド")
            ),
            Event.ON_TURN_END_5: Handler(
                lambda btl, val, ctx: hdl.reduce_global_field_count(btl, val, ctx, "terrain"),
            )
        },
    ),
    "サイコフィールド": FieldData(
        turn_extension_item="グランドコート",
        handlers={
            Event.ON_TURN_END_5: Handler(
                lambda btl, val, ctx: hdl.reduce_global_field_count(btl, val, ctx, "terrain"),
            )
        },
    ),
    "ミストフィールド": FieldData(
        turn_extension_item="グランドコート",
        handlers={
            Event.ON_TURN_END_5: Handler(
                lambda btl, val, ctx: hdl.reduce_global_field_count(btl, val, ctx, "terrain"),
            )
        },
    ),
    "じゅうりょく": FieldData(
        handlers={
            Event.ON_TURN_END_5: Handler(
                lambda btl, val, ctx: hdl.reduce_global_field_count(btl, val, ctx, "gravity"),
            ),
        },
    ),
    "トリックルーム": FieldData(
        handlers={
            Event.ON_TURN_END_5: Handler(
                lambda btl, val, ctx: hdl.reduce_global_field_count(btl, val, ctx, "trickroom"),
            ),
        },
    ),

    # Side fields
    "リフレクター": FieldData(
        handlers={
            Event.ON_CALC_DAMAGE_MODIFIER_BY_DEF: Handler(hdl.リフレクター),
            Event.ON_TURN_END_5: Handler(
                lambda btl, val, ctx: hdl.reduce_side_field_count(btl, val, ctx, "reflector"),
            ),
        },
    ),
    "ひかりのかべ": FieldData(
        handlers={
        },
    ),
    "しんぴのまもり": FieldData(
        handlers={
        },
    ),
    "しろいきり": FieldData(
        handlers={
        },
    ),
    "おいかぜ": FieldData(
        handlers={
        },
    ),
    "ねがいごと": FieldData(
        handlers={
        },
    ),
    "まきびし": FieldData(
        handlers={
        },
    ),
    "どくびし": FieldData(
        handlers={
        },
    ),
    "ステルスロック": FieldData(
        handlers={
        },
    ),
    "ねばねばネット": FieldData(
        handlers={
        },
    ),
}
