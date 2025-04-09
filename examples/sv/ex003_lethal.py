#######################################################
# 致死率計算 (ダメージ計算)
#######################################################

from pokejpy.sv.battle import *


# ---------------------------------------
# 入力
# ---------------------------------------
p1 = Pokemon('カイリュー')
p1.nature = 'いじっぱり'
# p1.initial_ability = ''
p1.item = Item('')
# p1.Ttype, p1.terastal = 'ステラ', True
p1.effort = [0, 252, 0, 0, 0, 0]
# p1.rank = [0, 0, 0, 0, 0, 0]
# p1.ailment = 'BRN'

p2 = Pokemon('ガチグマ(アカツキ)')
# p2.nature = 'ずぶとい'
# p2.initial_ability = ''
# p2.item = Item('オボンのみ')
# p2.Ttype, p2.terastal = 'フェアリー', True
p2.effort = [252, 0, 0, 0, 0, 0]
# p2.rank = [0, 0, 0, 0, 0, 0]
# p2.ailment = 'PSN'
# p2.condition['shiozuke'] = 1


# ポケモンをセット
battle = Battle()
battle.pokemon[0] = p1
battle.pokemon[1] = p2

# 攻撃側のプレイヤーindex
pidx = 0

# 攻撃技
move_list = ['しんそく']                    # 単発計算
# move_list = ['スケイルショット']           # 単発計算
# move_list = ['スケイルショット','じしん']   # 加算計算

critical = False                            # 急所
n_combo = 5                                 # 連続技のヒット数

# 盤面の状態
# battle.condition['sandstorm'] = 1         # 砂嵐
# battle.condition['glassfield'] = 1        # グラスフィールド
# battle.condition['reflector'] = [1, 1]    # リフレクター


# ---------------------------------------
# 計算結果
# ---------------------------------------
print(f"{p1}\n{'-'*50}")
print(f"{p2}\n{'-'*50}")
print(move_list)
print('\t', battle.lethal(pidx=pidx, move_list=move_list, n_combo=n_combo))
print(f"\t{battle.damage_dict.keys()=}")
print(f"\t{battle.damage_dict.values()=}")
print(f"\t{battle.lethal_num=}")
print(f"\t{battle.lethal_prob=:.3f}")
print(f"\t{battle.damage_log[pidx]=}")

# ---------------------------------------
# 1発あたりのダメージ
# ---------------------------------------
print('\n', move_list[0])
print('\t', '単発ダメージ', battle.oneshot_damages(pidx=pidx, move=move_list[0]))
