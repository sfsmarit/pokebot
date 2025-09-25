import json

from pokebot import PokeDB
import pokebot.common.utils as ut
from pokebot.common.enums import *

dict = {}

for name in PokeDB.abilities:
    dict[name] = {
        "flags": [],
        "effects": [],
        "handlers": [],
    }

    dict[name]["handlers"].append({
        "trigger": "on_start_1",
        "handler": f"{name}"
    })

for tag, abilities in PokeDB.tagged_abilities.items():
    tag = tag.replace("immediate", "on_start")
    tag = tag.replace("contact", "on_contact")
    tag = tag.replace("attack", "on_damage")
    tag = tag.replace("berry", "on_after_item")

    for name in abilities:
        if name not in dict:
            continue

        if tag in ["unreproducible", "protected", "undeniable", "one_time"]:
            dict[name]["flags"].append(tag)
        elif tag not in ["anti_ikaku"]:
            dict[name]["effects"].append({
                "trigger": tag,
                "target": "",
            })
            dict[name]["handlers"].clear()

# 表示
for k, v in dict.items():
    print(f"{k}\t{v}")

dst = ut.path_str("data", "ability.json")
with open(dst, "w", encoding="utf-8") as f:
    json.dump(dict, f, ensure_ascii=False, indent=4)
