import json

from pokebot import PokeDB
import pokebot.common.utils as ut
from pokebot.common.enums import *

keys = ["type", "category", "power", "pp", "hit"]

dict = {}

for name, data in PokeDB.move_data.items():
    dict[name] = {}
    for key in keys:
        dict[name][key] = data.__dict__[key]

    dict[name]["category"] = dict[name]["category"].value
    dict[name]["pp"] = int(dict[name]["pp"] * 5/8)
    if dict[name]["hit"] > 100:
        dict[name]["hit"] = 0

    dict[name]["priority"] = 0

    dict[name]["flags"] = []
    if data.category == MoveCategory.STA:
        if not data.protect:
            dict[name]["flags"].append("unprotectable")
        if not data.subst:
            dict[name]["flags"].append("ignore_substitute")
        if data.gold:
            dict[name]["flags"].append("blocked_by_gold")
        if data.mirror:
            dict[name]["flags"].append("reflectable")

    dict[name]["effects"] = []
    dict[name]["handlers"] = []

# 優先度
for data, v in PokeDB.move_priority.items():
    if data in dict:
        dict[data]["priority"] = v

# タグ
for tag, moves in PokeDB.tagged_moves.items():
    for data in moves:
        if data in dict:
            dict[data]["flags"].append(tag)

# 連続技
for data, rng in PokeDB.combo_range.items():
    if data in dict:
        dict[data]["flags"].append(f"combo_{rng[0]}_{rng[1]}")

for data, d in PokeDB.move_effect.items():
    if data not in dict:
        continue

    dict[data]["effects"].append({
        "trigger": "on_hit",
        "target": "opponent" if d["target"] == 1 else "self",
        "chance": d["prob"],
    })

    for k in list(d.keys())[2:]:
        if d[k] == 0:
            continue

        v = d[k]

        if k == "mis_recoil":
            k = "recoil"
            dict[data]["effects"][-1]["trigger"] = "on_miss"
        elif k == "cost":
            k = "recoil"
            dict[data]["effects"][-1]["trigger"] = "on_before_move"

        dict[data]["effects"][-1][k] = v
        if k == "flinch":
            dict[data]["effects"][-1]["chance"] = v
            dict[data]["effects"][-1][k] = 1

# 表示
for data, v in dict.items():
    print(f"{data}\t{v}")

dst = ut.path_str("data", "move.json")
with open(dst, "w", encoding="utf-8") as f:
    json.dump(dict, f, ensure_ascii=False, indent=4)
