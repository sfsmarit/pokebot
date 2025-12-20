from dataclasses import dataclass
from enum import Enum, auto


class HandlerResultFlag(Enum):
    NONE = None
    STOP_HANDLER = auto()
    STOP_EVENT = auto()


@dataclass
class HandlerOutput:
    value = None
    flag: HandlerResultFlag = HandlerResultFlag.NONE
