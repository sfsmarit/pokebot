from pokebot.core import Pokemon


def push(dstr: dict, key: str, value: int | float):
    """dictに要素を追加する。すでにkeyがあればvalueを加算する"""
    if key not in dstr:
        dstr[key] = value
    else:
        dstr[key] += value


def zero_ratio(dstr: dict) -> float:
    """(keyがゼロのvalue) / (全てのvalueの合計)"""
    n, n0 = 0, 0
    for key in dstr:
        n += dstr[key]
        if float(key) == 0:
            n0 += dstr[key]
    return n0/n


def offset_hp(hp_dstr: dict, v: int) -> dict:
    """hp_dictのすべてのkeyにvを足す"""
    result = {}
    for hp in hp_dstr:
        h = int(float(hp))
        new_hp = '0' if h == 0 else str(max(0, h+v))
        if new_hp != '0' and hp[-2:] == '.0':
            new_hp += '.0'
        push(result, new_hp, hp_dstr[hp])
    return result


def apply_berry_heal(user: Pokemon, hp_dstr: dict) -> dict:
    new_hp_dstr = {}

    for hp in hp_dstr:
        if hp == '0' or hp[-2:] == '.0':
            push(new_hp_dstr, hp, hp_dstr[hp])

        elif user.item.name in ['オレンのみ', 'オボンのみ']:
            if float(hp) <= 0.5*user.stats[0]:
                recovery = int(
                    user.stats[0]/4) if user.item.name == 'オボンのみ' else 10
                key = str(min(user.hp, int(float(hp)) + recovery)) + '.0'
                push(new_hp_dstr, key, hp_dstr[hp])
            else:
                push(new_hp_dstr, hp, hp_dstr[hp])

        elif user.item.name in ['フィラのみ', 'ウイのみ', 'マゴのみ', 'バンジのみ', 'イアのみ']:
            if float(hp)/user.stats[0] <= (0.5 if user.ability.name == 'くいしんぼう' else 0.25):
                key = str(int(float(hp)) + int(user.stats[0]/3)) + '.0'
                push(new_hp_dstr, key, hp_dstr[hp])
            else:
                push(new_hp_dstr, hp, hp_dstr[hp])

    return new_hp_dstr
