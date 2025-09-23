################################################################
# 入力遅延の測定
#   野生ポケモンなど、オフライン対戦の初期画面で実行する
################################################################

from pokejpy.sv.battle import *


n = 20  # 試験回数


filename = f"{g['log_dir']}/latency.log"
battle = Battle(mode=Battle.OFFLINE)

with open(filename, 'w', encoding='utf-8') as fout:
    print('画面移動なしの入力遅延を測定中...')
    wait_times = [i/10 for i in range(20)]  # 試験範囲

    # 画面遷移がないときの遅延を測定
    results = []

    for i, t in enumerate(wait_times):
        p0 = battle.battle_cursor_position()
        results.append(True)
        for j in range(n):
            pos = (p0+1+j) % 4
            battle.press_button('DPAD_DOWN', post_sleep=t)
            ans = battle.battle_cursor_position()
            print(f'\t{j+1}) {pos} {ans} {pos==ans}')
            if pos != ans:
                results[-1] = False
                break
            time.sleep(0.2)

        print(f'Delay: {t}s, Result: {results[-1]}')
        if len(results) >= 2 and results[-2] and results[-1]:
            fout.write(f'wo_screen_transition\t{wait_times[i-1]}\n')
            break

    battle.press_button('Y', post_sleep=0.5)
    battle.press_button('A', post_sleep=0.5)

    # 画面遷移があるときの遅延を測定
    print('画面移動ありの入力遅延を測定中...')

    results.clear()

    for i, t in enumerate(wait_times):
        results.append(True)
        for j in range(n):
            battle.press_button('B', post_sleep=0.3)
            battle.press_button('A', post_sleep=t)
            ans = battle.is_condition_window()
            print('\t', j+1, ':', ans)
            if not ans:
                results[-1] = False
                break
            time.sleep(0.2)

        print(f'Delay: {t}s, Result: {results[-1]}')
        if len(results) >= 2 and results[-2] and results[-1]:
            fout.write(f'w_screen_transition\t{wait_times[i-1]}\n')
            break

    battle.press_button('B', n=2, interval=0.5)
    print('測定完了')
