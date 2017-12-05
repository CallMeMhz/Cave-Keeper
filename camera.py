import config
from config import vec, WIDTH, HEIGHT
from pygame.transform import scale


class Camera:
    def __init__(self, game):
        self.game = game
        self.offset = vec(0, 0)

    def apply(self, entity):
        # entity.rect.topleft = entity.pos * config.TILESIZE
        entity.image = scale(entity.origin_image, (config.TILESIZE, config.TILESIZE))
        return entity.rect.move(self.offset)

    def update(self, vector):
        self.offset += vector
        self.repair()

    def focus(self, pos):
        self.offset = -pos
        self.repair()

    def repair(self):
        # 水平方向上避免显示最两端地图块
        self.offset.x = min(0, self.offset.x)
        self.offset.x = max(WIDTH - self.game.map.width * config.TILESIZE, self.offset.x)
        self.offset.y = min(0, self.offset.y)
        self.offset.y = max(HEIGHT - self.game.map.height * config.TILESIZE, self.offset.y)
