from pygame.math import Vector2
import itertools


def vec(*args, **kwargs):
    return Vector2(*args, **kwargs)


def vec2int(v):
    return tuple((int(v.x), int(v.y)))


def union_dicts(*dicts):
    return dict(itertools.chain.from_iterable(dct.items() for dct in dicts))

# colors (R, G, B)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARKGREY = (40, 40, 40)
LIGHTGREY = (100, 100, 100)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
BROWN = (106, 55, 5)

# game
WIDTH = 1024
HEIGHT = 768
FPS = 60
TITLE = 'Cave Keeper'
GAME_SPEED = 200

# map
TILESIZE = 48
FORBIDDEN_LENGTH = 5
