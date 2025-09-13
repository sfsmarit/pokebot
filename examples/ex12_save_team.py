"""
概要
    ボックス画面からパーティを読み込み、ファイルに書き出す

実行前の準備
    - ボックスを開き、手持ち/バトルチームの1匹目にカーソルを合わせる
    - プロコンを使用している場合は接続を切る
"""

from pokebot import Bot


# ------------------------------

#  保存先
team_file = "./team.json"

# ------------------------------

Bot.init_bot(video_id=0)
player = Bot()

# ボックス画面からパーティを読み取る
player.team = player.read_team_from_box()

# パーティの保存
player.save_team(team_file)

# パーティの読み込み
player.load_team(team_file)
