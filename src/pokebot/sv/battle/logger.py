from copy import deepcopy

from pokebot.sv.move import Move


class BattleLogger:
    """
    試合のログ全般を管理するクラス
    """

    def __init__(self):
        self.damage_logs = [[], []]


class DamageLogger:
    """
    ダメージ発生時の状況を保持するクラス
    """

    def __init__(self, battle, attacker_idx: int, move: Move):
        self.turn = battle.turn
        self.attacker_idx = attacker_idx
        self.pokemons = deepcopy(self.pokemons)
        self.move = deepcopy(move)
        self.damage_dealt = battle.damage_dealt[attacker_idx]
        self.damage_ratio = battle.damage_dealt[attacker_idx] / battle.pokemon[not attacker_idx].stats[0]
        self.critical = battle._critical
        self.stellar = battle.stellar[attacker_idx].copy()
        self.condition = battle.condition.copy()
        self.notes = []

    def mask(self):
        pass

    def is_estimable(self) -> bool:
        pass
