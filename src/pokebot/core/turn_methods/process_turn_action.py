from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Command, Ailment, Condition, MoveCategory
# from pokebot.common import PokeDB
from pokebot.pokedb import Move
from pokebot.logger import TurnLog

from pokebot.core.move_utils import num_strikes, hit_probability


def _process_turn_action(self: TurnManager, idx: PlayerIndex | int):
    attacker = self.battle.pokemons[idx]
    attacker_mgr = self.battle.poke_mgrs[idx]
    dfn = int(not idx)
    defender_mgr = self.battle.poke_mgrs[dfn]
    move = self.move[idx]

    # 行動直前の初期化
    self.init_act()

    # 行動スキップ
    if self.command[idx] == Command.SKIP:
        self.battle.logger.append(TurnLog(self.battle.turn, idx, '行動スキップ'))
        self.battle.poke_mgrs[idx].no_act()
        return

    # このターンに交代していたら行動不可
    if self._already_switched[idx]:
        return

    # みちづれ/おんねん解除
    self.battle.poke_mgrs[idx].count[Condition.MICHIZURE] = 0

    # 反動で動けない
    if not move.name:
        self.battle.logger.append(TurnLog(self.battle.turn, idx, '行動不能 反動'))
        self.battle.poke_mgrs[idx].no_act()
        return

    # ねむりカウント消費
    if attacker.ailment == Ailment.SLP:
        self.battle.poke_mgrs[idx].reduce_sleep_count(
            by=(2 if attacker.ability.name == 'はやおき' else 1))

    # ねむり行動不能
    if attacker.ailment == Ailment.SLP and "sleep" not in move.tags:
        self.battle.poke_mgrs[idx].no_act()
        return

    # こおり判定
    elif attacker.ailment == Ailment.FLZ:
        if "unfreeze" in move.tags or self.battle.random.random() < 0.2:
            attacker_mgr.set_ailment(Ailment.NONE)  # こおり解除
        else:
            self.battle.poke_mgrs[idx].no_act()
            self.battle.logger.append(TurnLog(self.battle.turn, idx, '行動不能 こおり'))
            return

    # なまけ判定
    if attacker.ability.name == 'なまけ':
        attacker.ability.count += 1
        if attacker.ability.count % 2 == 0:
            self.battle.poke_mgrs[idx].no_act()
            self.battle.logger.append(TurnLog(self.battle.turn, idx, '行動不能 なまけ'))
            return

    # ひるみ判定
    if self._flinch:
        self.battle.poke_mgrs[idx].no_act()
        self.battle.logger.append(TurnLog(self.battle.turn, idx, '行動不能 ひるみ'))
        if attacker.ability.name == 'ふくつのこころ':
            attacker_mgr.activate_ability()
        return

    # 挑発などにより選択できない技が選ばれていれば中断する
    if self.battle.poke_mgrs[idx].forced_turn == 0:
        is_choosable, reason = attacker_mgr.can_choose_move(move)
        if not is_choosable:
            self.battle.poke_mgrs[idx].no_act()
            self.battle.logger.append(TurnLog(self.battle.turn, idx, f"{move} 不発 ({reason})"))
            return

    # こんらん自傷判定
    if attacker_mgr.add_condition_count(Condition.CONFUSION, -1):
        if self.battle.random.random() < 0.25:
            mv = Move('わるあがき')
            damages = self.battle.damage_mgr.single_hit_damages(idx, mv, self_damage=True)
            self.battle.logger.insert(-1, TurnLog(self.battle.turn, idx, 'こんらん自傷'))
            attacker_mgr.add_hp(-self.battle.random.choice(damages), move=mv)
            self.battle.poke_mgrs[idx].no_act()
            return

    # しびれ判定
    if attacker.ailment == Ailment.PAR and self.battle.random.random() < 0.25:
        self.battle.poke_mgrs[idx].no_act()
        self.battle.logger.append(TurnLog(self.battle.turn, idx, '行動不能 しびれ'))
        return

    # メロメロ判定
    if self.battle.poke_mgrs[idx].count[Condition.MEROMERO] and self.battle.random.random() < 0.5:
        self.battle.poke_mgrs[idx].no_act()
        self.battle.logger.append(TurnLog(self.battle.turn, idx, '行動不能 メロメロ'))
        return

    # PPを消費する技の確定
    if move.name != 'わるあがき':
        self.battle.poke_mgrs[idx].expended_moves.append(move)

        # 命令可能な状態ならPPを消費する
        if self.battle.poke_mgrs[idx].forced_turn == 0:
            move.add_pp(-2 if self.battle.pokemons[dfn].ability.name == 'プレッシャー' else -1)
            move.observed = True  # 観測
            self.battle.logger.append(TurnLog(self.battle.turn, idx, f"{move} {move.pp}/{move._org_pp}"))

    # ねごとによる技の変更
    if move.name == 'ねごと':
        if self.can_execute_move(idx, move):
            move = self.battle.random.choice(attacker.get_negoto_moves())
            move.observed = True  # 観測
            self.battle.logger.append(TurnLog(self.battle.turn, idx, f"ねごと -> {move}"))
        else:
            self.move_succeeded[idx] = False

    # まもる技・場に出たターンしか使えない技の発動判定
    for tag in ['protect', 'first_turn']:
        self.move_succeeded[idx] &= self.can_execute_move(idx, move, tag=tag)

    # 発動する技の決定
    self.battle.poke_mgrs[idx].executed_move = move if self.move_succeeded[idx] else Move()

    # こだわり固定化
    if attacker.item.name[:4] == 'こだわり' or \
            attacker.ability.name == 'ごりむちゅう':
        self.battle.poke_mgrs[idx].choice_locked = True

    # 技の発動可否判定
    # 自爆技の判定も行う (本来はリベロ判定の後)
    self.move_succeeded[idx] &= self.can_execute_move(idx, move)

    # へんげんじざい判定
    if self.move_succeeded[idx] and \
            attacker.ability.name in ['へんげんじざい', 'リベロ']:
        attacker_mgr.activate_ability(move)

    # ため技の発動処理
    if any(tag in move.tags for tag in ["charge", "hide"]):
        # ためターン (0 or 1)
        self.battle.poke_mgrs[idx].forced_turn = int(self.battle.poke_mgrs[idx].forced_turn == 0)
        # 行動不能判定
        if self.battle.poke_mgrs[idx].forced_turn and not self.charge_move(idx, move):
            return

    # 隠れ状態の解除
    self.battle.poke_mgrs[idx].hidden = False

    # HPコストの消費
    if PokeDB.get_move_effect_value(move, "cost") and \
            self.move_succeeded[idx] and \
            attacker_mgr.apply_move_recoil(move, 'cost') and \
            self.battle.winner() is not None:
        return

    # 技が無効なら中断
    if not self.move_succeeded[idx]:
        self.battle.logger.append(TurnLog(self.battle.turn, idx, "技失敗"))
        return

    # 相手のまもる技により攻撃を防がれたら中断
    if self._protecting_move.name and self.process_protection(idx, move):
        return

    # 技の無効化 -> 技の効果処理に統合

    # 技の発動回数の決定
    self._n_strikes = num_strikes(self.battle, idx, move)
    if self._n_strikes > 1:
        self.battle.logger.append(TurnLog(self.battle.turn, idx, f"{self._n_strikes}発"))

    for cnt in range(self._n_strikes):
        # 命中判定
        if cnt == 0 or move.name in ["トリプルアクセル", "ネズミざん"]:
            is_hit = self.battle.random.random() < hit_probability(self.battle, idx, move)

        # 技を外したら中断
        if not is_hit:
            if cnt == 0:
                self.process_on_miss(idx, move)  # 1発目の外し
            else:
                self.battle.logger.append(TurnLog(self.battle.turn, idx, f"{cnt}ヒット"))
            break

        # 技の発動処理
        if move.category == MoveCategory.STA:
            self.process_status_move(idx, move)
        else:
            self.process_attack_move(idx, move, combo_count=cnt)

        if self.battle.winner() is not None:  # 勝敗判定
            return

        # 反射による攻守入れ替え
        if self._move_was_mirrored:
            idx, dfn = dfn, idx

        # 無効化特性の処理
        if self._move_was_negated_by_ability:
            self.process_negating_ability(dfn)

        # 即時アイテムの判定
        for i in [idx, dfn]:
            if self.battle.pokemons[i].item.immediate and self.battle.pokemons[i].hp:
                self.battle.poke_mgrs[i].activate_item()

        # 場のポケモンが瀕死なら攻撃を中断
        if not all(poke.hp for poke in self.battle.pokemons):
            break

    # 記録
    self.battle.poke_mgrs[idx].active_turn += 1
    self.battle.logger.append(TurnLog(self.battle.turn, idx, f"技{'成功' if self.move_succeeded[idx] else '失敗'}"))

    # ステラ強化タイプの消費
    self.consume_stellar(idx, move)

    # 反動による次ターンの行動不能を設定
    if self.move_succeeded[idx]:
        attacker_mgr.process_tagged_move(move, 'immovable')

    if self.damage_dealt[idx]:
        # 攻撃側の特性判定
        if self.battle.pokemons[idx].ability.name in \
                ['じしんかじょう', 'しろのいななき', 'じんばいったい', 'くろのいななき', 'マジシャン']:
            attacker_mgr.activate_ability()

        # 防御側の特性判定
        if self.battle.pokemons[dfn].ability.name in ['へんしょく', 'ぎゃくじょう', 'いかりのこうら']:
            defender_mgr.activate_ability(move)

        self.battle.poke_mgrs[dfn].berserk_triggered = False

        # 被弾アイテムの判定
        if self.battle.pokemons[dfn].hp and \
                self.battle.pokemons[dfn].item.name in ['レッドカード', 'アッキのみ', 'タラプのみ']:
            defender_mgr.activate_item(move)

        # 反動アイテムの判定
        if self.battle.pokemons[idx].item.name in ['いのちのたま', 'かいがらのすず']:
            attacker_mgr.activate_item()

    # TODO ききかいひ・にげごし判定
    # TODO わるいてぐせ判定
