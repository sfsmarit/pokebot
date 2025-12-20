from jpoke.utils.enums import Command
from jpoke.core.battle import Battle
from jpoke.player.player import Player


class MCTSPlayer(Player):
    def __init__(self, name: str = ""):
        super().__init__(name)

    def choose_action_command(self, battle: Battle) -> Command:
        commands = battle.get_available_action_commands(self)
