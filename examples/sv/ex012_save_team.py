############################################################################
# ボックス画面からパーティを読み込んでファイルに書き出す
#   ボックスの手持ち or バトルチームの1匹目にカーソルを合わせた状態で実行する
############################################################################

from pokejpy.sv.battle import *


# ------------------------------

#  保存するファイル
team_file = "./team.json"

# ------------------------------

# 対戦しないため、Battleインスタンスを直接生成する
battle = Battle(mode=BattleMode.OFFLINE)

# ボックス画面からパーティを読み取る
battle.player[0].team = battle.read_team_from_box()

# パーティの保存
battle.player[0].save_team(team_file)

# パーティの読み込み
battle.player[0].load_team(team_file)
