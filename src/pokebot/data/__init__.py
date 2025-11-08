from .ability import ABILITIES
from .item import ITEMS
from .move import MOVES

# 名前を追加
for data in [ABILITIES, ITEMS, MOVES]:
    for name, obj in data.items():
        if not isinstance(obj, dict):
            obj.name = name
