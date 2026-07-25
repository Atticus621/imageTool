from enum import Enum, auto


class InteractionMode(Enum):
    IDLE = auto()
    DRAWING_RECT = auto()
    DRAWING_CIRCLE = auto()
    DRAWING_POLYGON = auto()
    MOVING = auto()
    RESIZING_EDGE = auto()
    RESIZING_CORNER = auto()
    ROTATING = auto()
