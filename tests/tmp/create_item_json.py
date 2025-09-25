import json

from pokebot import PokeDB
import pokebot.common.utils as ut
from pokebot.common.enums import *

keys = ["consumable", "throw_power"]

dict = {}

for name, data in PokeDB.item_data.items():
    dict[name] = {}
    for key in keys:
        dict[name][key] = data.__dict__[key]

    dict[name]["flags"] = []
    dict[name]["effects"] = []
    dict[name]["handlers"] = []

    if data.immediate:
        dict[name]["effects"].append({
            "trigger": "on_update",
            "target": "self",
        })
    if data.triggers_on_hit:
        dict[name]["effects"].append({
            "trigger": "on_hit",
            "target": "self",
        })
    if data.buff_type != "None":
        dict[name]["effects"].append({
            "trigger": "on_modify_attack",
            "buff_type": data.buff_type,
        })
    if data.debuff_type != "None":
        dict[name]["effects"].append({
            "trigger": "on_modify_attack",
            "debuff_type": data.debuff_type,
        })
    if data.power_correction != 1:
        dict[name]["effects"].append({
            "trigger": "on_modify_attack",
            "modifier": data.power_correction,
        })


# 表示
for data, v in dict.items():
    print(f"{data}\t{v}")

dst = ut.path_str("data", "item.json")
with open(dst, "w", encoding="utf-8") as f:
    json.dump(dict, f, ensure_ascii=False, indent=4)
