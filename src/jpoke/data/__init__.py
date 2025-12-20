from .ability import ABILITIES
from .item import ITEMS
from .move import MOVES
from .field import FIELDS
from .ailment import AILMENTS


# 名前を追加
for data in [
    ABILITIES, ITEMS, MOVES, FIELDS, AILMENTS
]:
    for name, obj in data.items():
        if not isinstance(obj, dict):
            obj.name = name
