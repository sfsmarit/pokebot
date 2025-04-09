from enum import Enum, auto


class TestA(Enum):
    X = auto()


class TestB(Enum):
    X = auto()


d = {TestA.X: 'Aだよ', TestB.X: 'Bです', }


print(d[TestA.X], TestA.X.value)
print(d[TestB.X], TestB.X.value)
