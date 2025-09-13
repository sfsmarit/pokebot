"""
統計データの扱い
"""

import random
from pokebot import PokeDB


name = random.choice(list(PokeDB.name_to_kata_list.keys()))
# name = "コライドン"


print(f"{'-'*50}\n{name} のランクマッチ採用率\n{'-'*50}")

print(f"性格\t\t{PokeDB.home[name].natures}")
print(f"\t\t{PokeDB.home[name].nature_rates}")

print(f"特性\t\t{PokeDB.home[name].abilities}")
print(f"\t\t{PokeDB.home[name].ability_rates}")

print(f"アイテム\t{PokeDB.home[name].items}")
print(f"\t\t{PokeDB.home[name].item_rates}")

print(f"テラスタル\t{PokeDB.home[name].terastals}")
print(f"\t\t{PokeDB.home[name].terastal_rates}")

print(f"技\t\t{PokeDB.home[name].moves}")
print(f"\t\t{PokeDB.home[name].move_rates}")


print(f"{'='*50}\n{name}の型\n{'='*50}")

# 一部のポケモンは、型として登録されている名前に修正
if name in PokeDB.valid_kata_name:
    name = PokeDB.valid_kata_name[name]

for s in PokeDB.name_to_kata_list[name]:
    print(f"\t型名\t\t{s}")

    print(f"\t特性\t\t{PokeDB.kata[s].abilities}")
    print(f"\t\t\t{PokeDB.kata[s].ability_rates}")

    print(f"\tアイテム\t{PokeDB.kata[s].items}")
    print(f"\t\t\t{PokeDB.kata[s].item_rates}")

    print(f"\tテラスタル\t{PokeDB.kata[s].terastals}")
    print(f"\t\t\t{PokeDB.kata[s].terastal_rates}")

    print(f"\t技\t\t{PokeDB.kata[s].moves}")
    print(f"\t\t\t{PokeDB.kata[s].move_rates}")

    print(f"\t同じチーム\t{PokeDB.kata[s].teams}")
    print(f"\t\t\t{PokeDB.kata[s].team_rates}")

    print(f"\t同じチームの型\t{PokeDB.kata[s].team_kata}")
    print(f"\t\t\t{PokeDB.kata[s].team_kata_rates}")

    print('-'*50)
