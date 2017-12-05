import pygame as pg
import random
import config
from config import vec, vec2int
from tasks import Dig, Cut, Carry, Build
from tiles import Ladder, Shelf, Bed, Torch

class Spritesheet(object):
    def __init__(self, filename):
        self.spritesheet = pg.image.load(filename).convert_alpha()

    def get_image(self, x, y, w, h):
        image = pg.Surface((w, h))
        image.blit(self.spritesheet, (0, 0), (x, y, w, h))
        image = pg.transform.scale(image, (config.TILESIZE, config.TILESIZE))
        return image


class Wood(pg.sprite.Sprite):
    def __init__(self, game, pos):
        self._layer = 1
        self.groups = game.all_sprites, game.items, game.woods
        pg.sprite.Sprite.__init__(self, self.groups)
        self.game = game
        self.origin_image = self.game.img['wood']
        self.image = self.origin_image
        self.rect = self.image.get_rect()
        self.pos = pos
        self.float_pos = vec2int(pos)
        self.v = vec()
        self.rect.topleft = self.pos * config.TILESIZE
        self.owner = None

    def update(self):
        self.rect.topleft = config.TILESIZE * self.pos
        self.float_pos = vec2int(config.TILESIZE * self.pos)

        if self.owner:
            self.pos = vec(self.owner.pos)
        # 掉落，用来临时解决脚下方块消失的问题
        while not self.game.map.can_stand(self.pos):
            self.pos.y += 1

        self.v = config.TILESIZE * self.pos - self.rect.topleft


class Imp(pg.sprite.Sprite):
    def __init__(self, game, pos):
        self._layer = 2
        self.groups = game.all_sprites, game.imps
        pg.sprite.Sprite.__init__(self, self.groups)
        self.game = game
        self.standing_image_l = self.game.img['imp']
        self.standing_image_r = pg.transform.flip(self.standing_image_l, True, False)
        self.origin_image = random.choice((self.standing_image_l, self.standing_image_r))
        self.image = self.origin_image
        self.rect = self.image.get_rect()
        self.pos = pos
        self.float_pos = pos
        self.v = vec()
        self.rect.topleft = self.pos * config.TILESIZE
        self.task = None
        self.hp = 5
        self.inventories = list()

    def move(self, v, force=False):
        if force:
            self.pos += v
            return

        # 假定目标点
        pos = self.pos + v
        if v.x:
            dirs = []
            if self.game.map.can_stand(pos):  # front
                dirs.append(pos)
            if self.game.map.can_stand(pos + (0, -1)):  # above
                dirs.append(pos + (0, -1))
            if self.game.map.can_stand(pos + (0, 1)):  # below
                dirs.append(pos + (0, 1))
            if dirs:
                self.pos = random.choice(dirs)
        elif v.y:
            pos = self.pos + v
            if self.game.map.in_bounds(pos) and self.game.map.can_stand(pos):
                self.pos = pos

    def hangout(self):
        neighbors = [self.pos + (x, y) for x in range(-1, 2) for y in range(-1, 2)]
        neighbors = [n for n in neighbors if self.game.map.can_stand(n) and self.game.map.in_bounds(n)]
        if neighbors:
            self.pos = random.choice(neighbors)

    def find(self, pos):
        path = self.game.map.path_finding(pos)
        if vec2int(self.pos) in path:
            vel = path[vec2int(self.pos)]
            if vel:
                self.move(vel, True)
                return 1  # 没到达目的地
            return 2  # 到达目的地
        return 0  # 没有路径可以走

    def update(self):
        # Control
        # keys = pg.key.get_pressed()
        # if keys[pg.K_LEFT]:
            # self.move(x = -1)
        # elif keys[pg.K_RIGHT]:
            # self.move(x = 1)
        # elif keys[pg.K_UP]:
            # self.move(y = -1)
        # elif keys[pg.K_DOWN]:
            # self.move(y = 1)

        self.rect.topleft = config.TILESIZE * self.pos
        self.float_pos = vec2int(config.TILESIZE * self.pos)
        pos = vec(self.pos)  # 拷贝原坐标，用于后面更新朝向

        if isinstance(self.task, Dig) or isinstance(self.task, Cut):
            if vec2int(self.task.target) not in self.game.map.groups['dig&cut_mark']:
                self.task = None
            else:
                find_res = self.find(self.task.dest)
                if find_res == 2:  # 到达目的地，开始敲
                    # random.choice(self.game.snd['digging']).play()
                    if isinstance(self.task, Dig):
                        random.choice(self.game.snd['digging']).play()
                    elif isinstance(self.task, Cut):
                        self.game.snd['cut_tree'].play()
                    if self.game.map.data[vec2int(self.task.target)].hit(-1) <= 0:
                        if isinstance(self.task, Cut):
                            self.game.snd['tree_down'].play()
                            neighbors = self.game.map.find_neighbors(self.task.target, (self.game.map.can_stand, ))
                            neighbors.append(self.task.target)
                            for i, neighbor in enumerate(neighbors):
                                if i < 3:
                                    Wood(self.game, neighbor)
                elif find_res == 1:  # 在路上
                    pass
                elif find_res == 0:  # 无法到达，游荡
                    self.task = None
        elif isinstance(self.task, Carry):
            if not self.task.item_to_find:  # 去放木头
                if vec2int(self.task.target + (0, 1)) not in self.game.map.groups['resource_mark']:
                    self.task = None
                else:
                    find_res = self.find(self.task.dest)
                    if find_res == 2:
                        wood = [i for i in self.inventories if isinstance(i, Wood)][0]
                        self.inventories.remove(wood)
                        wood.owner = None
                        self.task = None
                    elif find_res == 1:
                        pass
                    elif find_res == 0:
                        self.task = None
                    # if find_res != 1: self.state = Hangout() 用这个简练点？
            else:  # 去捡木头
                if self.task.item_to_find.owner is not None:
                    self.task = None
                else:
                    find_res = self.find(self.task.dest)
                    if find_res == 2:
                        self.task.item_to_find.owner = self
                        self.inventories.append(self.task.item_to_find)
                        self.task = None
                    elif find_res == 1:
                        pass
                    elif find_res == 0:
                        self.task = None
        elif isinstance(self.task, Build):
            if vec2int(self.task.target) not in self.game.map.groups['build_mark']:
                self.task = None
            else:
                find_res = self.find(self.task.dest)
                if find_res == 2:  # 到达目的地，开始敲
                    random.choice(self.game.snd['build']).play()
                    tile_to_built = self.game.map.data[vec2int(self.task.target)]
                    hp = tile_to_built.hit(+1)
                    if tile_to_built.image_name == 'ladder' and hp >= 3:
                        tile_to_built.kill()
                        Ladder(self.game.map, tile_to_built.pos)
                        self.game.consume_woods(1)
                    elif tile_to_built.image_name == 'shelf' and hp >= 6:
                        tile_to_built.kill()
                        Shelf(self.game.map, tile_to_built.pos)
                        self.game.consume_woods(3)
                    elif tile_to_built.image_name == 'bed' and hp >= 6:
                        tile_to_built.kill()
                        Bed(self.game.map, tile_to_built.pos)
                        self.game.consume_woods(4)
                    elif tile_to_built.image_name == 'torch' and hp >= 1:
                        tile_to_built.kill()
                        Torch(self.game.map, tile_to_built.pos)
                elif find_res == 1:  # 在路上
                    pass
                elif find_res == 0:  # 无法到达，游荡
                    self.task = None
        elif self.task is None:
                self.hangout()

        # 掉落，用来临时解决脚下方块消失的问题
        while not self.game.map.can_stand(self.pos):
            self.pos.y += 1

        # repair image orient
        if self.pos.x != pos.x:
            if self.pos.x < pos.x:
                self.origin_image = self.standing_image_l
            elif self.pos.x > pos.x:
                self.origin_image = self.standing_image_r

        self.v = config.TILESIZE * self.pos - self.rect.topleft
