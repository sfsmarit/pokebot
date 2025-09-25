class EventManager:
    def __init__(self) -> None:
        self.handlers = {}

    def on(self, event, func):
        """イベントにハンドラを登録"""
        self.handlers.setdefault(event, []).append(func)

    def emit(self, event, *args, **kwargs):
        """イベントを発火"""
        for func in self.handlers.get(event, []):
            func(*args, **kwargs)


class Pokemon:
    def __init__(self, name) -> None:
        self.name = name
        self.hp = 30


class Battle:
    def __init__(self, p1, p2) -> None:
        self.p1 = p1
        self.p2 = p2

        self.events = EventManager()
        self.events.on("move", self.apply_damage)

    def advance_turn(self):
        self.events.emit("move", self.p1, self.p2)
        self.events.emit("move", self.p2, self.p1)

    def apply_damage(self, attacker, defender):
        print(f"{defender.name=}")
        damage = 10
        defender.hp -= damage
        if defender.hp <= 0:
            print("倒れた")


if __name__ == "__main__":
    p1 = Pokemon("リザードン")
    p2 = Pokemon("カメックス")

    battle = Battle(p1, p2)

    battle.advance_turn()
