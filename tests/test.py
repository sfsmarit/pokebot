import json
from pokebot.model import PokeDB
import pokebot.common.utils as ut

# p1 = PokeDB.create_pokemon("リザードン")
# p1.show()

filename = ut.path_str("static", "move.json")

data = {}
for key, val in PokeDB.move.items():
    d = val.__dict__
    data[key] = {k: v for k, v in d.items() if
                 v != [] and k not in ["name", "handlers"]}


with open(filename, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
