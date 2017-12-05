import pygame as pg
import random
import math
import json
import os
from collections import deque
import config
from config import vec, vec2int, WIDTH, HEIGHT, FORBIDDEN_LENGTH, BLACK, DARKGREY, WHITE
from tiles import Dirt, Tree, Grass, Stone, RedStone, IronOre, Rock, EmeraldOre
from opensimplex import OpenSimplex


class Map(object):
    def __init__(self, game):
        self.game = game
        self.width = 0
        self.height = 0
        self.data = {}
        self.path_cache = {}
        self.groups = {
            'background': {},
            'block': {},
            'passable': {},
            'diggable': {},
            'cuttable': {},
            'destroyable': {},  # ~~~
            'earth': {},
            'visible': {},
            'visited': {},
            'light': {},
            'fbd': {},
            'dig&cut_mark': {},
            'resource_mark': {},
            'build_mark': {},
            'build_mark_noworker': {},
            'dirt': {},
            'sand': {},
            'stone': {},
            'redstone': {},
            'ironore': {},
            'emeraldore': {},
            'tree': {},
            'trunk': {},
            'leaf': {},
            'grass': {},
            'ladder': {},
            'torch': {},
            'shelf': {},
            'bed': {}
        }

        # forbidden zone
        self.fbd_tile = pg.Surface((1, 1))
        self.fbd_tile.fill(DARKGREY)
        self.fbd_tile.set_alpha(128)

        # black tile
        self.black_tile = pg.Surface((1, 1))
        self.black_tile.fill(BLACK)

        # buildings
        self.leaders = list()

        # load images from game resource
        self.image = {}
        tiles_sheet = json.load(open(os.path.join(self.game.img_dir, 'tiles/tiles_sheet.json')))
        for tile_name in tiles_sheet:
            self.image[tile_name] = pg.image.load(os.path.join(self.game.img_dir, 'tiles/' + tile_name + '.png')).convert_alpha()
        self.image['ladder'] = pg.image.load(os.path.join(self.game.img_dir, 'tiles/ladder.png')).convert()
        self.image['ladder'].set_colorkey(BLACK)
        self.image['shelf'] = pg.image.load(os.path.join(self.game.img_dir, 'tiles/shelf.png')).convert()
        self.image['bed'] = pg.image.load(os.path.join(self.game.img_dir, 'tiles/bed.png')).convert()
        self.image['bed'].set_colorkey(BLACK)

    @staticmethod
    def set_grey(image, alpha):
        grey_mask = pg.Surface(image.get_rect().size)
        grey_mask.fill(BLACK)
        grey_mask.set_alpha(alpha)
        image.blit(grey_mask, (0, 0))
        return image

    def generate(self, w, h):
        self.width, self.height = w, h
        self.data = {(x, y): None for x in range(self.width) for y in range(self.height)}
        self.path_cache = {}

        noise = OpenSimplex(seed=random.randint(-100000, 100000))
        base = 20
        last_tree_x = 0
        for col in range(w):
            hh = base + int(noise.noise2d(0, col/10) * 10)
            hh = max(10, hh)
            hh = min(self.height - 10, hh)
            r = random.random()
            if r < .3:
                if col - last_tree_x >= 3:
                    Tree(self, vec(col, hh - 1))
                    last_tree_x = col
            elif .3 < r < .6:
                Grass(self, vec(col, hh - 1))
            elif .6 < r < .7:
                Rock(self, vec(col, hh - 1))
            for row in range(hh, h):
                if row == hh:
                    last_tile = Dirt(self, vec(col, row))
                    last_tile.image_name = 'dirt_grass'
                elif row < hh + 4:
                    last_tile = Dirt(self, vec(col, row))
                else:
                    r = noise.noise2d(col/10, row/10)
                    # r = noise.noise3d(col/10, row/10, noise.noise2d(col/10, row/10))
                    if -1 < r < -.8:
                        last_tile = EmeraldOre(self, vec(col, row))
                    elif -.8 < r < -.5:
                        last_tile = RedStone(self, vec(col, row))
                    elif .15 < r < .2:
                        last_tile = Dirt(self, vec(col, row))
                    elif .6 < r < 1:
                        last_tile = IronOre(self, vec(col, row))
                    else:
                        last_tile = Stone(self, vec(col, row))

    def find_neighbors(self, pos, filters):
        dirs = [(x, y) for x in range(-1, 2) for y in range(-1, 2)]
        dirs.remove((0, 0))  # 去掉中点
        neighbors = [pos + dir for dir in dirs]
        neighbors = [n for n in neighbors if self.in_bounds(n)]
        for func in filters:
            neighbors = [n for n in neighbors if func(n)]
        return neighbors

    def path_finding(self, target):
        if vec2int(target) in self.path_cache:
            return self.path_cache[vec2int(target)]
        frontier = deque()
        frontier.append(target)
        path = dict()
        path[vec2int(target)] = None
        while len(frontier) > 0:
            current = frontier.popleft()
            for next in self.find_neighbors(current, (self.can_stand, )):
                if vec2int(next) not in path:
                    frontier.append(next)
                    path[vec2int(next)] = current - next
        if vec2int(target) not in self.path_cache:
            self.path_cache[vec2int(target)] = path
        return path

    def in_bounds(self, pos):
        if FORBIDDEN_LENGTH <= pos[0] < self.width - FORBIDDEN_LENGTH and \
           FORBIDDEN_LENGTH <= pos[1] < self.height - FORBIDDEN_LENGTH:
            return True
        return False

    @staticmethod
    def in_map(pos):
        if 0 <= pos[0] < WIDTH and \
           0 <= pos[1] < HEIGHT:
            return True
        return False

    def can_stand(self, pos):
        tile = self.data[vec2int(pos)]
        tile_below = self.data[vec2int(pos + (0, 1))]
        if tile is not None and tile.in_group('passable'):
            return True
        if tile_below and tile_below.in_group('block'):
            if (tile is None) or (tile and not tile.in_group('block')):
                return True
        return False

    def in_view(self, pos):
        if vec2int(pos) in self.groups['visited']:
            return True
        return False

    @staticmethod
    def resize(image):
        if image.get_rect().size == (config.TILESIZE, config.TILESIZE):
            return image
        return pg.transform.scale(image, (config.TILESIZE, config.TILESIZE))

    def draw(self, camera):
        # 返回绘制的地图块数量
        drawn = 0

        # 计算屏幕笼罩区域
        row_start = int(-camera.offset.y / config.TILESIZE)
        row_end = int((-camera.offset.y + HEIGHT) / config.TILESIZE) + 1
        col_start = int(-camera.offset.x / config.TILESIZE)
        col_end = int((-camera.offset.x + WIDTH) / config.TILESIZE) + 1
        for row in range(row_start, row_end):
            for col in range(col_start, col_end):
                pos = vec(col, row)
                scr_pos = pos * config.TILESIZE + camera.offset
                tile = self.data[vec2int(pos)] if vec2int(pos) in self.data else None  # 防止渲染出界

                if vec2int(pos) in self.groups['visited'] or True:
                    if tile is not None:
                        if hasattr(tile, 'bg_name'):
                            image = self.resize(self.image[tile.bg_name])
                            if hasattr(tile, 'bg_grey') and tile.bg_grey:
                                image = self.set_grey(image, 100)
                            fg_image = self.image[tile.image_name].copy()
                            if hasattr(tile, 'alpha'):
                                fg_image.set_alpha(tile.alpha)
                            image.blit(self.resize(fg_image), (0, 0))
                        else:
                            image = self.resize(self.image[tile.image_name])
                            if hasattr(tile, 'alpha'):
                                image.set_alpha(tile.alpha)
                            if hasattr(tile, 'grey') and tile.grey:
                                image = self.set_grey(image, 100)
                        self.game.screen.blit(image, scr_pos)
                        drawn += 1

                    # draw forbidden area
                    if not self.in_bounds(pos):
                        fbd_tile = self.resize(self.fbd_tile)
                        self.game.screen.blit(fbd_tile, scr_pos)

                    # draw resource area
                    if tile and tile.in_group('resource_mark'):
                        image = self.resize(self.image['resource_mark'])
                        self.game.screen.blit(image, scr_pos)

                    if vec2int(pos) not in self.groups['visible']:
                        image = self.black_tile.copy()
                        image.set_alpha(180)
                        self.game.screen.blit(self.resize(image), scr_pos)
                else:
                    image = self.black_tile.copy()
                    self.game.screen.blit(self.resize(image), scr_pos)

                # draw mark
                if tile and tile.in_group('dig&cut_mark'):
                    dirs = [vec(x, y) for x in range(-1, 2) for y in range(-1, 2)]
                    dirs.remove(vec(0, 0))
                    found = 0
                    for neighbor in [tile.pos + dir for dir in dirs]:
                        neighbor = self.data[vec2int(neighbor)]
                        if neighbor and self.can_stand(neighbor.pos):
                            found += 1
                    if found:
                        self.game.screen.blit(self.resize(self.game.img['dig_mark_hammer']), scr_pos)
                    else:
                        self.game.screen.blit(self.resize(self.game.img['dig_mark']), scr_pos)

        return drawn

    def clear_path_cache(self):
        self.path_cache = {}

    def light(self, pos, view_radius=5, skip=6):  # TODO light fade
        for angle in range(0, 360, skip):
            v = vec(math.cos(angle * 0.01745), math.sin(angle * 0.01745))
            o = pos + (0.5, 0.5)
            block = False
            for i in range(view_radius):
                if not block:
                    tile = self.data[vec2int(o)]
                    self.groups['visible'][vec2int(o)] = tile
                    self.groups['visited'][vec2int(o)] = tile
                    # if tile and tile.in_group('block'):
                    #     block = True
                    o += v
                    if not self.in_map(o):
                        block = True

    def light_torch(self):
        for torch_pos in self.groups['torch']:
            self.light(vec(torch_pos), self.groups['torch'][torch_pos].range)
