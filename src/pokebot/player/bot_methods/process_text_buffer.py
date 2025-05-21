from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot_player import BotPlayer

from pokebot.common import PokeDB
from pokebot.model import Pokemon, Item


def _process_text_buffer(self: BotPlayer):
    """テキストバッファの情報を反映させる"""
    new_buffer = []
    move_order = []

    for i, dict in enumerate(self.text_buffer):
        idx = dict['idx']
        poke = Pokemon.find_most_similar(self.battle.selected_pokemons(idx), label=dict['label'])
        poke_mgr = self.battle.poke_mgrs[idx]

        if not poke:
            print(f"{dict['label']} is not in Player{idx}'s team")
            new_buffer.append(dict)  # 情報を保持
            continue

        if 'ability' in dict:
            poke.ability.name = dict['ability']
            if poke.ability.name == 'ばけのかわ':
                poke.ability.active = False
            poke.ability.observed = True  # 観測

        elif 'item' in dict:
            if poke.item != dict['item']:
                poke.item = Item(dict['item'])
            poke_mgr.choice_locked = False
            poke.item.observed = True  # 観測

        elif 'lost_item' in dict:
            if poke.item != dict['item']:
                poke.item = Item(dict['item'])
            poke.item.active = False
            if poke.item.name_lost == 'ブーストエナジー' and poke.name == self.battle.pokemons[idx].name:
                poke_mgr.boosted = True
            poke_mgr.choice_locked = False
            poke.item.observed = True  # 観測

        elif 'subst' in dict:
            if dict['subst']:
                pass
            else:
                poke_mgr.sub_hp = 0

        elif 'type' in dict:
            poke_mgr.lost_types, poke_mgr.added_types = poke_mgr.types, [dict['type']]

        elif 'boost' in dict:
            poke_mgr.boosted_idx = dict['boost_idx']

        elif 'move' in dict:
            if i > 1 and 'move' in self.text_buffer[i-1] and \
                    self.text_buffer[i-1]['idx'] == idx and \
                    self.text_buffer[i-1]['move'] in PokeDB.move_tag['call']:
                # ねごとなど、1ターンに2度技の演出がある場合
                poke_mgr.executed_move = poke.find_move(dict['move'])

                if idx == 1 and \
                        poke_mgr.expended_moves and \
                        poke_mgr.expended_moves[-1] == 'ねごと' and \
                        poke_mgr.executed_move:
                    poke.add_move(poke_mgr.executed_move.name)
                    poke.moves[-1].observed = True  # 観測
            else:
                # その他の技
                if idx == 1 and not poke.knows(dict['move']):
                    poke.add_move(dict['move'])
                    poke.moves[-1].observed = True  # 観測

                move = poke.find_move(dict['move'])
                poke_mgr.expended_moves.append(move)
                poke_mgr.executed_move = move

                if move:
                    # いま場にプレッシャーのポケモンがいればPPを2減らす
                    move.add_pp(-2 if self.battle.pokemons[not idx].ability.name == 'プレッシャー' else -1)

                    # TODO 相手の行動を記録
                    pass

                # 発動した技を記録
                if not move_order or move_order[-1]['idx'] != idx:
                    move_order.append(dict)

            self.battle.turn_mgr.move_succeeded[idx] = dict['hit']

            # 技の効果を反映させる
            if self.battle.turn_mgr.move_succeeded[idx]:
                match poke_mgr.executed_move:
                    case 'でんこうそうげき':
                        poke.lost_types.append('でんき')
                    case 'もえつきる':
                        poke.lost_types.append('ほのお')
                    case 'みがわり':
                        poke.sub_hp = int(poke.stats[0]/4)
                    case 'しっぽきり':
                        selected = self.battle.selected_pokemons(idx)
                        if (p1 := Pokemon.find(selected, name=self.pokemons[idx].name)):
                            p1.sub_hp = int(poke.stats[0]/4)
                    case 'バトンタッチ':
                        selected = self.battle.selected_pokemons(idx)
                        if poke.sub_hp and (p1 := Pokemon.find(selected, name=self.pokemons[idx].name)):
                            p1.sub_hp = poke.sub_hp

    # 処理できなかった情報を持ち越す
    # 試合開始の認識精度が悪いため、オフライン対戦では持ち越さない
    self.text_buffer = new_buffer if self.online else []

    # 両プレイヤーが使用した技の優先度が同じなら、行動順から素早さを推定する
    if len(move_order) == 2 and move_order[0]['move_speed'] == move_order[1]['move_speed']:

        # 相手の行動順index
        oidx = [dict['idx'] for dict in move_order].index(1)

        poke = Pokemon.find(self.battle.selected_pokemons(1), label=move_order[oidx]['label'])

        if poke is None:
            print(f"{move_order[oidx]['label']} is not in \
                              {[p.label for p in self.battle.selected_pokemons(1)]}")
        else:
            # 相手のS補正値
            r_speed = move_order[oidx]['eff_speed'] / move_order[oidx]['speed']

            # 相手のS = 自分のS / 相手のS補正値
            speed = int(move_order[not oidx]['eff_speed'] / r_speed)

            # S推定値を更新
            poke.set_speed_limit(speed, first_act=(oidx == 0))
