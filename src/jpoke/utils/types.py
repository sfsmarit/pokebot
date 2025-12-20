from typing import Literal


GLOBAL_FIELDS = Literal["weather", "terrain", "gravity", "trickroom"]

SIDE_FIELDS = Literal["reflector", "lightwall", "shinpi", "whitemist",
                      "oikaze", "wish",
                      "makibishi", "dokubishi", "stealthrock", "nebanet"]

WEATHERS = Literal["はれ", "あめ", "ゆき", "すなあらし"]

TERRAINS = Literal["エレキフィールド", "グラスフィールド",
                   "サイコフィールド", "ミストフィールド"]
