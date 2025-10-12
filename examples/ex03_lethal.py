"""
任意の対面を設定して致死率を計算する
"""


from pokebot import Pokemon, Battle, Player, enums


battle = Battle(Player(), Player())
battle.init_game()

# ------------------------------ プレイヤー0 ------------------------------
poke = Pokemon('カイリュー')
poke.level = 50
poke.nature = 'いじっぱり'
# poke.ability = "ちからもち"
poke.item = ""
poke.terastal = "ステラ"
# poke.terastallize()  # テラスタル発動 (実際の対戦と同様にフォルムチェンジ等も行う)
# poke.is_terastallized = True  # テラスタル発動 (テラスタル以外の状態は不変)
poke.effort = [0, 252, 0, 0, 0, 0]  # 努力値 [H, A, B, C, D, S]
# poke.ailment = enums.Ailment.BRN  # 状態異常

# battle.poke_mgrs[0].rank[1] = +2  # 能力ランク [H, A, B, C, D, S]
# battle.poke_mgrs[0].boosted_idx = 1  # 能力ブースト


battle.player[0].team.append(poke)
battle.player[0].team[0].active = True  # 場に出す

# ------------------------------ プレイヤー1 ------------------------------
poke = Pokemon('ガチグマ(アカツキ)')
# poke.level = 50
poke.nature = 'ずぶとい'
# poke.ability = "マルチスケイル"
# poke.item = 'オボンのみ'
# poke.terastal = "フェアリー"
# poke.terastallize()
poke.effort = [252, 0, 0, 0, 0, 0]
# poke.ailment = enums.Ailment.PSN

# battle.poke_mgrs[1].rank[2] = +2  # 能力ランク [H, A, B, C, D, S]
# battle.poke_mgrs[1].boosted_idx = 2  # 能力ブースト [H, A, B, C, D, S]

battle.player[1].team.append(poke)
battle.player[1].team[0].active = True  # 場に出す

# ------------------------------ その他 ------------------------------

attacker_idx = 0  # 攻撃側のプレイヤー番号

# moves = ['しんそく']
# moves = ['スケイルショット']
moves = ['しんそく', 'じしん']  # 加算計算

critical = False  # 急所判定
combo_hits = 5  # 連続技のヒット数

battle.field_mgr.set_weather(enums.Weather.SUNNY, idx=0)  # 天候
battle.field_mgr.count[enums.Terrain.GRASS] = 1  # フィールド
battle.field_mgr.count[enums.GlobalField.GRAVITY] = 1  # じゅうりょく
battle.field_mgr.count[enums.SideField.REFLECTOR][not attacker_idx] = 1  # リフレクター
battle.field_mgr.count[enums.SideField.LIGHT_WALL][not attacker_idx] = 1  # ひかりのかべ


print(f"{battle.pokemons[0]}\n{'-'*50}")
print(f"{battle.pokemons[1]}\n{'-'*50}")

# ---------------------------------------
# 致死率計算
# ---------------------------------------
result = battle.damage_mgr.lethal(
    attacker_idx,
    move_list=moves,  # type: ignore
    combo_hits=combo_hits,
)

print("致死率計算")
print(f"{moves}\t{result}")
print(f"ダメージ\t{battle.damage_mgr.damage_dstr.keys()}")
print(f"ダメージ分布\t{battle.damage_mgr.damage_dstr.values()}")
print(f"確定数\t\t{battle.damage_mgr.lethal_num}")
print(f"致死率\t\t{battle.damage_mgr.lethal_prob:.3f}")
print(f"計算ログ\t{battle.damage_mgr.log.notes}")
print('-'*50)

# ---------------------------------------
# 1発あたりのダメージ
# ---------------------------------------
damages = battle.damage_mgr.single_hit_damages(attacker_idx, moves[0])
print("単発ダメージ")
print(f"{moves[0]}\t{damages}")
