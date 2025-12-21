from typing import Literal


AILMENT = Literal["", "どく", "もうどく", "まひ", "やけど", "ねむり", "こおり"]

GLOBAL_FIELD = Literal["weather", "terrain", "gravity", "trickroom"]

SIDE_FIELD = Literal["reflector", "lightwall", "shinpi", "whitemist",
                     "oikaze", "wish",
                     "makibishi", "dokubishi", "stealthrock", "nebanet"]

WEATHER = Literal["はれ", "あめ", "ゆき", "すなあらし"]

TERRAIN = Literal["エレキフィールド", "グラスフィールド", "サイコフィールド", "ミストフィールド"]
