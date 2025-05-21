#######################################################

# 統計データの見方
#######################################################

from pokejpy.sv.battle import *


Player()  # モジュールの初期化


name = 'ペリッパー'
# name = random.choice(list(Pokemon.home.keys()))
# name = random.choice(list(Pokemon.name2kata.keys()))


print(f"{'-'*50}\n{name} のランクマッチ採用率\n{'-'*50}")

print(f"性格\t\t{Pokemon.home[name]['nature']}")
print(f"\t\t{Pokemon.home[name]['nature_rate']}")

print(f"特性\t\t{Pokemon.home[name]['ability']}")
print(f"\t\t{Pokemon.home[name]['ability_rate']}")

print(f"アイテム\t{Pokemon.home[name]['item']}")
print(f"\t\t{Pokemon.home[name]['item_rate']}")

print(f"テラスタル\t{Pokemon.home[name]['terastal']}")
print(f"\t\t{Pokemon.home[name]['terastal_rate']}")

print(f"技\t\t{Pokemon.home[name]['move']}")
print(f"\t\t{Pokemon.home[name]['move_rate']}")


if name in Pokemon.name2name:
    name = Pokemon.name2name[name]  # 名前の修正

if name in Pokemon.name2kata:
    print(f"{'='*50}\n{name} の型\n{'='*50}")
    for s in Pokemon.name2kata[name]:
        print(f"\t型名\t\t{s}")

        print(f"\t特性\t\t{Pokemon.kata[s]['abilities']}")

        print(f"\tアイテム\t{Pokemon.kata[s]['items']}")

        print(f"\tテラスタル\t{Pokemon.kata[s]['terastals']}")

        print(f"\t技\t\t{Pokemon.kata[s]['moves']}")

        print(f"\t同じチーム\t{Pokemon.kata[s]['teammates']}")

        print(f"\t同じチーム(型)\t{Pokemon.kata[s]['teammates_kata']}")
