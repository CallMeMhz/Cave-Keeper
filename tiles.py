from config import vec2int
import random


class Tile(object):
    def __init__(self, map, pos, groups):
        self.map = map
        self.pos = pos  # 用于 kill 自己
        self.map.data[vec2int(pos)] = self
        self.groups = list(groups)
        for group in self.groups:
            self.map.groups[group][vec2int(pos)] = self
        self.hp = 1
        self.map.clear_path_cache()

    def add_to_group(self, group):
        self.map.groups[group][vec2int(self.pos)] = self
        self.groups.append(group)

    def remove_from_group(self, group):
        self.map.groups[group].pop(vec2int(self.pos))
        self.groups.remove(group)

    def in_group(self, group):
        if vec2int(self.pos) in self.map.groups[group]:
            return True
        return False

    def kill(self):
        bg_tile = None
        if hasattr(self, 'bg_name'):
            bg_tile = BgTile(self.map, self.pos, self.bg_name, self.bg_grey)
        self.map.data[vec2int(self.pos)] = bg_tile
        for group in self.groups:
            self.map.groups[group].pop(vec2int(self.pos))
        self.map.clear_path_cache()

    def hit(self, p):
        self.hp += p
        if self.hp <= 0:
            self.kill()
        return self.hp


class Dirt(Tile):
    def __init__(self, map, pos):  # edge 标记了边缘方位
        groups = ('block', 'diggable', 'dirt', 'earth')
        Tile.__init__(self, map, pos, groups)
        r = random.random()
        if r < .85:
            self.image_name = 'dirt'
        else:
            self.image_name = 'gravel_dirt'
        self.hp = 5

    def kill(self):
        super().kill()
        if self.image_name == 'dirt_grass':
            BgTile(self.map, self.pos, 'dirt_grass', grey=True)
        else:
            r = random.random()
            if r < .95:
                BgTile(self.map, self.pos, 'dirt', grey=True)
            else:
                BgTile(self.map, self.pos, 'gravel_dirt', grey=True)


class Sand(Tile):
    def __init__(self, map, pos):
        groups = ('block', 'diggable', 'sand', 'earth')
        Tile.__init__(self, map, pos, groups)
        self.image_name = 'sand'
        self.hp = 3

    def kill(self):
        super().kill()
        BgTile(self.map, self.pos, 'sand', grey=True)


class Stone(Tile):
    def __init__(self, map, pos):
        groups = ('block', 'diggable', 'stone', 'earth')
        Tile.__init__(self, map, pos, groups)
        r = random.random()
        if r < .95:
            self.image_name = 'stone'
        else:
            self.image_name = 'gravel_stone'
        self.hp = 8

    def kill(self):
        super().kill()
        r = random.random()
        if r < .95:
            BgTile(self.map, self.pos, 'stone', grey=True)
        else:
            BgTile(self.map, self.pos, 'gravel_stone', grey=True)


class RedStone(Tile):
    def __init__(self, map, pos):
        groups = ('block', 'diggable', 'redstone', 'earth')
        Tile.__init__(self, map, pos, groups)
        self.image_name = 'redsand'
        self.hp = 10

    def kill(self):
        super().kill()
        BgTile(self.map, self.pos, 'redsand', grey=True)


class EmeraldOre(Tile):
    def __init__(self, map, pos):
        groups = ('block', 'diggable', 'emeraldore', 'earth')
        Tile.__init__(self, map, pos, groups)
        self.image_name = random.choice(['redstone_emerald', 'redstone_emerald_alt'])
        self.hp = 10

    def kill(self):
        super().kill()
        BgTile(self.map, self.pos, 'redstone', grey=True)


class IronOre(Tile):
    def __init__(self, map, pos):
        groups = ('block', 'diggable', 'ironore', 'earth')
        Tile.__init__(self, map, pos, groups)
        self.image_name = random.choice(['stone_iron', 'stone_iron_alt'])
        self.hp = 10

    def kill(self):
        super().kill()
        r = random.random()
        if r < .95:
            BgTile(self.map, self.pos, 'stone', grey=True)
        else:
            BgTile(self.map, self.pos, 'gravel_stone', grey=True)


class Tree(Tile):
    def __init__(self, map, pos):
        groups = ('tree', 'cuttable')
        Tile.__init__(self, map, pos, groups)
        self.image_name = 'trunk_bottom'
        self.hp = 5
        self.leaves = [Leaf(map, pos + (x, y)) for x in range(-1, 2) for y in range(-4, -1)]
        self.leaves = [leaf for leaf in self.leaves if leaf is not None]
        self.trunk = Trunk(map, pos + (0, -1))

    def kill(self):
        super().kill()
        for leaf in self.leaves:
            leaf.kill()
        self.trunk.kill()


class Leaf(Tile):
    def __init__(self, map, pos):
        if not map.in_map(vec2int(pos)) or map.data[vec2int(pos)] is not None:
            return
        groups = ('leaf', )
        Tile.__init__(self, map, pos, groups)
        self.image_name = 'leaves_transparent'


class Trunk(Tile):
    def __init__(self, map, pos):
        groups = ('trunk', )
        Tile.__init__(self, map, pos, groups)
        self.image_name = 'trunk_mid'


class Shelf(Tile):
    def __init__(self, map, pos):
        groups = ('shelf', 'destroyable')
        Tile.__init__(self, map, pos, groups)
        self.image_name = 'shelf'
        self.hp = 5

    def kill(self):
        super().kill()


class Bed(Tile):
    def __init__(self, map, pos):
        groups = ('bed', 'destroyable')
        bg_tile = map.data[vec2int(pos)]
        if bg_tile:
            self.bg_name = bg_tile.image_name
            self.bg_grey = bg_tile.grey
        Tile.__init__(self, map, pos, groups)
        self.image_name = 'bed'
        self.hp = 5

    def kill(self):
        super().kill()


class Ladder(Tile):
    def __init__(self, map, pos):
        groups = ('passable', 'ladder', 'destroyable')
        bg_tile = map.data[vec2int(pos)]
        if bg_tile:
            self.bg_name = bg_tile.image_name
            self.bg_grey = bg_tile.grey
        Tile.__init__(self, map, pos, groups)
        self.image_name = 'ladder'


class Torch(Tile):
    def __init__(self, map, pos, range=5):
        groups = ('light', 'torch', 'destroyable')
        bg_tile = map.data[vec2int(pos)]
        if bg_tile:
            self.bg_name = bg_tile.image_name
            self.bg_grey = bg_tile.grey
        Tile.__init__(self, map, pos, groups)
        self.image_name = 'tochLit'
        self.range = range


class BgTile(Tile):
    def __init__(self, map, pos, image, grey=False):
        groups = ('background', )
        Tile.__init__(self, map, pos, groups)
        self.image_name = image
        self.grey = grey


class Grass(BgTile):
    def __init__(self, map, pos):
        groups = ('grass', )
        BgTile.__init__(self, map, pos, groups)
        self.image_name = random.choice(['grass{}'.format(i) for i in range(1, 5)] +
                                        ['wheat_stage{}'.format(i) for i in range(1, 5)])


class Rock(BgTile):
    def __init__(self, map, pos):
        groups = ('rock', )
        BgTile.__init__(self, map, pos, groups)
        self.image_name = random.choice(['rock', 'rock_moss'])


class BuildMark(Tile):
    def __init__(self, map, pos, image_name, worker=None):
        groups = ('build_mark', 'build_mark_noworker', )
        bg_tile = map.data[vec2int(pos)]
        if bg_tile:
            self.bg_name = bg_tile.image_name
            self.bg_grey = bg_tile.grey
        Tile.__init__(self, map, pos, groups)
        self.image_name = image_name
        self.alpha = 128
        self.hp = 0
