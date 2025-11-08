from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..turn_manager import TurnManager

from pokebot.common.types import PlayerIndex
from pokebot.common.enums import Ailment, Condition
from pokebot.common.constants import STAT_CODES
# from pokebot.common import PokeDB
from pokebot.model import Move
from pokebot.logger import TurnLog

from pokebot.core.move_utils import critical_probability


def _process_attack_move(self: TurnManager,
                         atk: PlayerIndex | int,
                         move: Move,
                         combo_count: int):

    dfn = int(not atk)
    attacker = self.battle.pokemons[atk]
    defender = self.battle.pokemons[dfn]
    attacker_mgr = self.battle.poke_mgrs[atk]
    defender_mgr = self.battle.poke_mgrs[dfn]
    damage_mgr = self.battle.damage_mgr

    # 急所判定
    critical = self.battle.random.random() < critical_probability(self.battle, atk, move)
    if critical:
        self.battle.logger.add(TurnLog(self.battle.turn, atk, '急所'))

    if move.power > 0:
        # ダメージ計算
        r = 1
        if move.name == 'トリプルアクセル':
            r += combo_count

        damages = damage_mgr.single_hit_damages(atk, move, critical=critical, power_multiplier=r)
        self.damage_dealt[atk] = self.battle.random.choice(damages) if damages else 0

        # ダメージログに記録
        self.battle.damage_mgr.log.damage_dealt = self.damage_dealt[atk]
        self.battle.damage_mgr.log.damage_ratio = self.damage_dealt[atk] / defender.stats[0]

        # ダメージ発生状況を記録
        if self.damage_dealt[atk] and not any(self.battle.call_count):
            self.battle.logger.add(self.battle.damage_mgr.log)

    else:
        # 特殊ダメージの処理
        self.process_special_damage(atk, move)

        # 勝敗判定 (いのちがけ処理)
        if self.battle.winner() is not None:
            return

    # ダメージが0なら中断
    if not self.damage_dealt[atk]:
        attacker_mgr.forced_turn = 0
        self.move_succeeded[atk] = False
        return

    # 壁破壊
    attacker_mgr.process_tagged_move(move, 'wall_break')

    # みがわり被弾判定
    self._hit_substitute = defender_mgr.sub_hp > 0 and \
        attacker.ability.name != 'すりぬけ' and \
        "sound" not in move.tags

    # ダメージ付与
    if self._hit_substitute:
        # みがわり被弾
        self.damage_dealt[atk] = min(defender_mgr.sub_hp, self.damage_dealt[atk])
        defender_mgr.sub_hp -= self.damage_dealt[atk]

        if defender_mgr.sub_hp:
            self.battle.logger.add(TurnLog(self.battle.turn, dfn, f"みがわりHP {defender_mgr.sub_hp}"))
        else:
            self.battle.logger.add(TurnLog(self.battle.turn, dfn, "みがわり消滅"))

    elif defender_mgr.defending_ability(move).name == 'ばけのかわ':
        # ばけのかわ被弾
        self.damage_dealt[atk] = 0
        defender_mgr.add_hp(ratio=-1/8)
        self.battle.logger.insert(-1, TurnLog(self.battle.turn, dfn, defender.ability.name))
        defender.ability.active = False

    else:
        # ダメージ修正
        self.modify_damage(atk)

        # ダメージ付与
        defender_mgr.add_hp(-self.damage_dealt[atk], move=move)
        self.battle.logger.add(TurnLog(self.battle.turn, atk, f"ダメージ {self.damage_dealt[atk]}"))
        self.battle.logger.add(TurnLog(self.battle.turn, atk, f"相手{self.battle.pokemons[dfn].name} HP {self.battle.pokemons[dfn].hp}"))

        # 被弾回数を記録
        defender_mgr.hits_taken += 1

    # ダメージ発生時に発動したアイテムの消費
    for i, poke_mgr in enumerate(self.battle.poke_mgrs):
        if self.battle.damage_mgr.log.item_consumed[i]:
            poke_mgr.consume_item()

    # 勝敗判定
    if self.battle.winner() is not None:
        return

    # 追加効果の判定
    if move.name in PokeDB.move_effect:
        effect = PokeDB.move_effect[move.name]
        tgt = ((atk + effect["target"]) % 2)
        target_mgr = self.battle.poke_mgrs[tgt]

        r_prob = 2 if attacker.ability.name == 'てんのめぐみ' else 1
        if self.battle.is_test:
            self.battle.r_prob = r_prob  # type: ignore

        if (tgt == atk or defender_mgr.can_receive_move_effect(move)) and \
                (self.battle.is_test or self.battle.random.random() < effect['prob'] * r_prob):
            # ランク変動
            delta = [0] + [effect[s] for s in STAT_CODES[1:]]
            if any(delta):
                if target_mgr.add_rank(values=delta):
                    self.battle.logger.insert(-1, TurnLog(self.battle.turn, atk, '追加効果'))

            # 状態異常
            candidates = [ailment for ailment in Ailment if ailment.value and effect[ailment.name]]
            if any(candidates):
                ailment = self.battle.random.choice(candidates)
                if target_mgr.set_ailment(ailment, bad_poison=(effect["PSN"] == 2)):
                    self.battle.logger.insert(-1, TurnLog(self.battle.turn, atk, '追加効果'))

            # こんらん
            if effect['confusion']:
                if target_mgr.set_condition(Condition.CONFUSION, self.battle.random.randint(2, 5)):
                    self.battle.logger.add(TurnLog(self.battle.turn, atk, '追加効果 こんらん'))

    # ひるみ判定
    self._flinch = self.check_flinch(atk, move)

    # 技の追加効果
    if move.name in ['アンカーショット', 'かげぬい', 'サイコノイズ', 'しおづけ',
                     'じごくづき', 'なげつける', 'みずあめボム']:
        attacker_mgr.activate_move_effect(move)

    # HP吸収
    if (r_drain := PokeDB.get_move_effect_value(move, "drain")) and \
            self.damage_dealt[atk] and \
            attacker_mgr.add_hp(attacker_mgr.hp_drain_amount(int(r_drain * self.damage_dealt[atk]))):
        self.battle.logger.insert(-1, TurnLog(self.battle.turn, atk, "吸収"))

    if self._hit_substitute:
        # みがわりを攻撃したら与ダメージ0を記録
        self.damage_dealt[atk] = 0

    else:
        # 技の追加処理 (ダメージ付与時)
        if move.name in ['おんねん', 'くちばしキャノン', 'クリアスモッグ', 'コアパニッシャー']:
            attacker_mgr.activate_move_effect(move)

        # 攻撃側の特性
        if "attack" in attacker.ability.flags:
            attacker_mgr.activate_ability(move)

        # 防御側の特性
        if any(tag in defender.ability.flags for tag in ['damage', 'contact']):
            defender_mgr.activate_ability(move)

    # やきつくす判定
    if move.name == 'やきつくす':
        attacker_mgr.activate_move_effect(move)

    # 被弾時に発動するアイテムの判定
    if defender.item.triggers_on_hit:
        defender_mgr.activate_item(move)

    # みちづれ判定
    if defender_mgr.count[Condition.MICHIZURE] and defender.hp == 0:
        attacker.hp = 0
        self.battle.logger.add(TurnLog(self.battle.turn, atk, '瀕死 みちづれ'))
        self.move_succeeded[dfn] = True
        return

    # 技の反動付与
    attacker_mgr.apply_move_recoil(move, "recoil")

    # バインド付与
    attacker_mgr.process_tagged_move(move, "bind")

    # 追加効果の判定
    if move.name in [
        'わるあがき', 'がんせきアックス', 'キラースピン', 'こうそくスピン', 'ひけん・ちえなみ', 'プラズマフィスト',
        'うちおとす', 'サウザンアロー', 'きつけ', 'くらいつく', 'サウザンウェーブ', 'ついばむ', 'むしくい',
        'とどめばり', 'ドラゴンテール', 'ともえなげ', 'どろぼう', 'ほしがる', 'はたきおとす', 'めざましビンタ',
        'うたかたのアリア', 'ぶきみなじゅもん',
    ] or (move.name == 'スケイルショット' and combo_count == self._n_strikes - 1):
        attacker_mgr.activate_move_effect(move)

    # 相手のこおり状態解除
    if defender.ailment == Ailment.FLZ and \
            self.damage_dealt[atk] and \
            (move.type == 'ほのお' or "unfreeze" in move.tags):
        defender_mgr.set_ailment(Ailment.NONE)
