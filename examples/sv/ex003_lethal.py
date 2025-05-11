#######################################################
# 致死率計算 (ダメージ計算)
#######################################################

from pokebot import Pokemon, Battle, RandomPlayer


# ---------------------------------------
# 入力
# ---------------------------------------
p1 = Pokemon('カイリュー')
p1.nature = 'いじっぱり'
# p1.ability = ""
p1.item = ""
# p1.Ttype = "ステラ"
# p1.terastallize()
p1.effort = [0, 252, 0, 0, 0, 0]
# p1.rank = [0, 0, 0, 0, 0, 0]

p2 = Pokemon('ガチグマ(アカツキ)')
# p2.nature = 'ずぶとい'
# p2.ability = ""
# p2.item = Item('オボンのみ')
# p2.Ttype = "フェアリー"
# p2.terastallize()
p2.effort = [252, 0, 0, 0, 0, 0]
# p2.rank = [0, 0, 0, 0, 0, 0]

# プレイヤーをセット
battle = Battle(RandomPlayer([p1]), RandomPlayer([p2]))
battle.init_game()

# ポケモンを場に出す
battle.player[0].team[0].active = True
battle.player[1].team[0].active = True

# 攻撃側のプレイヤーindex
idx = 0

# 攻撃技
# moves = ['しんそく']
moves = ['スケイルショット']
# moves = ['スケイルショット','じしん']

critical = False
combo_hits = 5

# 盤面の状態
# battle.field_mgr.set_weather(Weather.SAND)
# battle.condition['glassfield'] = 1        # グラスフィールド
# battle.condition['reflector'] = [1, 1]    # リフレクター


# ---------------------------------------
# 計算結果
# ---------------------------------------
print(f"{p1}\n{'-'*50}")
print(f"{p2}\n{'-'*50}")
print(moves)
print(f"結果\t\t{battle.damage_mgr.lethal(idx, move_list=moves, combo_hits=combo_hits)}")
print(f"ダメージ\t{battle.damage_mgr.damage_dstr.keys()}")
print(f"ダメージ分布\t{battle.damage_mgr.damage_dstr.values()}")
print(f"確定数\t\t{battle.damage_mgr.lethal_num}")
print(f"致死率\t\t{battle.damage_mgr.lethal_prob:.3f}")
print(f"計算ログ\t{battle.damage_mgr.log.notes}")

# ---------------------------------------
# 1発あたりのダメージ
# ---------------------------------------
print('\n', moves[0])
print('\t', '単発ダメージ', battle.damage_mgr.single_hit_damages(idx, moves[0]))
