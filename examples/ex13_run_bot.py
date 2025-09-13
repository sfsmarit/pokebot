"""
概要
    実機対戦を行う

実行前の準備
    - オフライン対戦なら、学校最強大会に参加する
    - オンライン対戦なら、対戦の待機画面に移動する
    - プロコンを使用している場合は接続を切る
"""


from pokebot import Bot
Bot.init_bot(video_id=0)


# ------------------------------

# パーティ (ex12で作成)
team_file = "./team.json"

# プレイヤーモデル
player = Bot()
opponent = Bot()
player.action_command = player.max_damage_command  # 方策関数を上書き

# True: オンライン対戦, False: 学校最強大会
online = True

# ------------------------------


# パーティの読み込み
player.load_team(team_file)

# 試合
while True:
    player.game(opponent, online=online)
