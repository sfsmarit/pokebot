from pokebot.common.enums import Command
from pokebot.core.battle import Battle
from pokebot.player.player import Player


class MCTSPlayer(Player):
    def __init__(self, name: str = ""):
        super().__init__(name)

    def choose_action_command(self, battle: Battle) -> Command:
        commands = battle.get_available_action_commands(self)
