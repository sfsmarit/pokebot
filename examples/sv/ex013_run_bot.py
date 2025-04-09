#######################################################
# 実機Bot (ランダム行動)
#   オフライン対戦を実行 : python ex014_bot.py
#   オンライン対戦を実行 : python ex014_bot.py 1
#######################################################

from pokejpy.sv.player import *


# ------------------------------

# パーティ (ex012_save_team.py で作成)
team_file = "team.json"

# プレイヤー
player = MaxDamagePlayer()

# ------------------------------


# パーティの読み込み
player.load_team(team_file)

# 実行時の引数でオフライン/オンラインを指定
mode = BattleMode.OFFLINE if len(sys.argv) == 1 else BattleMode.ONLINE

# 試合
while 1:
    player.game(mode=mode)
