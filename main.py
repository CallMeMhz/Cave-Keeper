import pygame as pg
import config
from config import vec, vec2int, TITLE, WIDTH, HEIGHT, WHITE, BROWN, RED, BLACK, union_dicts
from camera import Camera
from tasks import Dig, Cut, Carry, Build
from tilemap import Map
from tiles import Tree, BgTile, Torch, BuildMark
from sprites import Imp, Wood
from os import path
import random


class Game(object):
    def __init__(self):
        pg.mixer.pre_init(44100, -16, 1, 512)
        pg.init()
        pg.mixer.init()
        pg.display.set_caption(TITLE)
        pg.mouse.set_visible(False)
        self.screen = pg.display.set_mode((WIDTH, HEIGHT))
        self.clock = pg.time.Clock()

        # game
        self.running = True
        self.playing = False
        self.game_speed = 0
        self.last_update = 0
        self.dt = 0
        self.cursor_pos = vec()
        self.last_mouse_pos = vec()
        self.dragging_camera = False
        self.dragging_camera = False
        # Groups
        self.all_sprites = []
        self.items = []
        self.imps = []
        self.woods = []
        # Switcher
        self.map = None
        self.camera = None
        self.pause = False
        self.mode = None
        self.modes = [None, 'dig&cut', 'resource', 'imp', 'ladder', 'torch', 'shelf', 'bed']
        self.dragging = 0  # 0: False, 1: add, -1:remove

        # ----- load data -----
        self.dir = path.dirname(__file__)
        self.img_dir = path.join(self.dir, 'img')
        self.snd_dir = path.join(self.dir, 'snd')
        self.map_dir = path.join(self.dir, 'map')

        # load font
        self.font_name = path.join(self.dir, 'old_evils.ttf')

        # load images
        self.img = {
            'sky': pg.image.load(path.join(self.img_dir, 'Other/skybox_sideHills.png')).convert(),
            'sky_top': pg.image.load(path.join(self.img_dir, 'Other/skybox_top.png')).convert(),
            'sky_bottom': pg.image.load(path.join(self.img_dir, 'Other/skybox_bottom.png')).convert(),
            'dig_mark': pg.image.load(path.join(self.img_dir, 'dig_mark.png')).convert_alpha(),
            'dig_mark_hammer': pg.image.load(path.join(self.img_dir, 'dig_mark_hammer.png')).convert_alpha(),
            'imp': pg.image.load(path.join(self.img_dir, 'imp.png')).convert_alpha(),
            'wood': pg.image.load(path.join(self.img_dir, 'wood.png')).convert_alpha(),
            'cursor': pg.image.load(path.join(self.img_dir, 'cursor.png')).convert_alpha(),
            'axe_iron': pg.image.load(path.join(self.img_dir, 'Items/axe_iron.png')).convert_alpha(),
        }
        self.img['wood'].set_colorkey(BLACK)

        # load musics and sounds
        self.snd = {
            'mark': pg.mixer.Sound(path.join(self.snd_dir, 'mark1.ogg')),
            'unmark': pg.mixer.Sound(path.join(self.snd_dir, 'unmark1.ogg')),
            'digging': list(),
            'cut_tree': pg.mixer.Sound(path.join(self.snd_dir, 'qubodupImpactWood.ogg')),
            # 'dig_stone': [pg.mixer.Sound(path.join(self.snd_dir, 'qubodupImpactStone.ogg')),
            #               pg.mixer.Sound(path.join(self.snd_dir, 'qubodupImpactMetal.ogg'))],
            'shift': pg.mixer.Sound(path.join(self.snd_dir, 'UI_Click_Organic_mono.ogg')),
            'tree_down': pg.mixer.Sound(path.join(self.snd_dir, 'crack01.mp3.flac')),
            'build': [pg.mixer.Sound(path.join(self.snd_dir, 'qubodupImpactMeat01.ogg')),
                      pg.mixer.Sound(path.join(self.snd_dir, 'qubodupImpactMeat02.ogg'))]
        }

        for i in range(1, 9):
            self.snd['digging'].append(pg.mixer.Sound(path.join(self.snd_dir, 'tool{}.ogg'.format(i))))

    def new(self):
        self.dragging_camera = False
        self.all_sprites = pg.sprite.LayeredUpdates()
        self.items = pg.sprite.Group()
        self.imps = pg.sprite.Group()
        self.woods = pg.sprite.Group()
        self.map = Map(self)
        self.map.generate(200, 200)
        self.map.light(vec(10, 10), 20, 1)
        self.camera = Camera(self)
        self.game_speed = 200

        self.pause = False
        self.mode = None
        self.dragging = 0  # 0: False, 1: add, -1:remove

        pg.mixer.music.load(path.join(self.snd_dir, 'ObservingTheStar.ogg'))

        Imp(self, vec(10, 10))
        self.camera.focus(vec(10*config.TILESIZE, 10*config.TILESIZE))

        self.resource = {
            'woods': 0,
            'iron': 0,
        }

    def run(self):
        pg.mixer.music.play(loops=-1)
        pg.mixer.music.set_volume(0.4)
        self.playing = True
        self.last_update = pg.time.get_ticks()
        while self.playing:
            self.dt = self.clock.tick(config.FPS) / 1000
            self.events()
            self.update()
            self.draw()

    def update(self):
        if not self.pause:
            now = pg.time.get_ticks()
            if now - self.last_update > self.game_speed:
                self.last_update = now
                self.next_turn()

            for sprite in self.all_sprites:
                sprite.float_pos += sprite.v / ((self.game_speed - 14) / 1000) / config.FPS
                sprite.rect.topleft = sprite.float_pos

        mouse_pos = vec(pg.mouse.get_pos())
        self.cursor_pos = vec(vec2int((mouse_pos - self.camera.offset) / config.TILESIZE))
        tile = self.map.data[vec2int(self.cursor_pos)]
        # drag camera
        if self.dragging_camera:
            mouse_vector = mouse_pos - self.last_mouse_pos
            self.camera.update(mouse_vector)

        # game stuff
        if self.map.in_bounds(self.cursor_pos) and self.map.in_view(self.cursor_pos):
            if self.mode == 'dig&cut' and tile and (tile.in_group('destroyable') or
                                                    tile.in_group('diggable') or
                                                    tile.in_group('cuttable')):
                if self.dragging == 1:
                    if not tile.in_group('dig&cut_mark'):
                        tile.add_to_group('dig&cut_mark')
                        self.snd['mark'].play()
                elif self.dragging == -1:
                    if tile.in_group('dig&cut_mark'):
                        tile.remove_from_group('dig&cut_mark')
            elif self.mode == 'ladder':
                if self.dragging == 1:
                    if tile is None or isinstance(tile, BgTile):
                        # Ladder(self.map, self.cursor_pos)
                        BuildMark(self.map, self.cursor_pos, 'ladder')
                elif self.dragging == -1:
                    if isinstance(tile, BuildMark) and tile.image_name == 'ladder':
                        tile.kill()
            elif self.mode == 'shelf':
                if self.dragging == 1:
                    if tile is None or isinstance(tile, BgTile):
                        BuildMark(self.map, self.cursor_pos, 'shelf')
                elif self.dragging == -1:
                    if isinstance(tile, BuildMark) and tile.image_name == 'shelf':
                        tile.kill()
            elif self.mode == 'bed':
                if self.dragging == 1:
                    if tile is None or isinstance(tile, BgTile):
                        BuildMark(self.map, self.cursor_pos, 'bed')
                elif self.dragging == -1:
                    if isinstance(tile, BuildMark) and tile.image_name == 'bed':
                        tile.kill()
            elif self.mode == 'resource' and tile and tile.in_group('earth'):
                if self.dragging == 1:
                   if not tile.in_group('resource_mark') and \
                      self.map.can_stand(tile.pos + (0, -1)):
                       tile.add_to_group('resource_mark')
                       self.snd['mark'].play()
                elif self.dragging == -1:
                    if tile.in_group('resource_mark'):
                        tile.remove_from_group('resource_mark')
                        self.snd['unmark'].play()

        self.last_mouse_pos = mouse_pos

    def next_turn(self):

        # ----- 遍历标记，为标记雇佣 imp -----
        for mark in union_dicts(self.map.groups['dig&cut_mark'], self.map.groups['build_mark_noworker']):
            tile = self.map.data[mark]
            neighbors = self.map.find_neighbors(tile.pos, (self.map.can_stand, ))
            found = False
            for dest in neighbors:
                if not found:
                    path = self.map.path_finding(dest)
                    for imp in self.imps:
                        if not found:
                            if imp.task is None and vec2int(imp.pos) in path:
                                if tile and (tile.in_group('diggable') or tile.in_group('destroyable')):
                                    imp.task = Dig(self.map, tile.pos, dest)
                                    found = True
                                elif tile and tile.in_group('cuttable'):
                                    imp.task = Cut(self.map, tile.pos, dest)
                                    found = True
                                elif isinstance(tile, BuildMark):
                                    if (tile.image_name == 'torch') or \
                                       (tile.image_name == 'ladder' and self.resource['woods'] >= 1) or \
                                       (tile.image_name == 'shelf' and self.resource['woods'] >= 3) or \
                                       (tile.image_name == 'bed' and self.resource['woods'] >= 4):
                                        imp.task = Build(self.map, tile.pos, dest)
                                        tile.worker = imp
                                        tile.remove_from_group('build_mark_noworker')
                                        found = True
        # # ----- 更新小弟目的地 -----
        # for imp in self.imps:
        #     if isinstance(imp.task, Dig) or isinstance(imp.task, Cut):
        #         imp.task.path = {}
        #         neighbors = self.map.find_neighbors(imp.task.target, (self.map.can_stand,))
        #         found = False
        #         for dest in neighbors:
        #             if not found:
        #                 path = self.map.path_finding(dest)
        #                 if vec2int(imp.pos) in path:
        #                     imp.task.path = path
        #                     found = True
        for wood in self.woods:
            tile_below = self.map.data[vec2int(wood.pos + (0, 1))]
            if not wood.owner and tile_below and not tile_below.in_group('resource_mark'):
                path = self.map.path_finding(wood.pos)
                found = False
                for imp in self.imps:
                    if not found:
                        if imp.task is None and vec2int(imp.pos) in path and \
                           len([i for i in imp.inventories if isinstance(i, Wood)]) < 1:
                            imp.task = Carry(self.map, wood.pos, wood.pos, item_to_find=wood)

        for mark in self.map.groups['resource_mark']:
            path = self.map.path_finding(vec(mark) + (0, -1))
            for wood in self.woods:
                if wood.owner and vec2int(wood.owner.pos) in path:
                    wood.owner.task = Carry(self.map, vec(mark) + (0, -1), vec(mark) + (0, -1), item_to_find=None)

        self.all_sprites.update()

        self.map.groups['visible'] = {}
        for imp in self.imps:
            self.map.light(imp.pos)
        self.map.light_torch()

    def consume_woods(self, n):
        for i, wood_in_res in enumerate([wood for wood in self.woods if vec2int(wood.pos + vec(0, 1)) in self.map.groups['resource_mark']]):
            if i < n:
                wood_in_res.kill()

    def events(self):
        tile = self.map.data[vec2int(self.cursor_pos)]
        for e in pg.event.get():
            # ----- 退出事件 -----
            if e.type == pg.QUIT:
                if self.playing:
                    self.playing = False
                self.running = False
            # ----- 退出事件 -----

            # ----- 鼠标按下事件 -----
            if e.type == pg.MOUSEBUTTONDOWN:
                # e.button 1左键 2中键 3右键 4滚轮上 5滚轮下
                if e.button == 1:
                    if self.map.in_bounds(self.cursor_pos) and self.map.in_view(self.cursor_pos):
                        if self.mode == 'imp':
                            if self.map.can_stand(self.cursor_pos):
                                Imp(self, self.cursor_pos)
                        elif self.mode == 'shelf':
                            if tile is None or isinstance(tile, BgTile):
                                self.dragging = 1
                            elif isinstance(tile, BuildMark) and tile.image_name == 'ladder':
                                self.dragging = -1
                        elif self.mode == 'bed':
                            if tile is None or isinstance(tile, BgTile):
                                self.dragging = 1
                            elif isinstance(tile, BuildMark) and tile.image_name == 'bed':
                                self.dragging = -1
                        elif self.mode == 'ladder':
                            if tile is None or isinstance(tile, BgTile):
                                self.dragging = 1
                            elif isinstance(tile, BuildMark) and tile.image_name == 'ladder':
                                self.dragging = -1
                        elif self.mode == 'dig&cut' and tile:
                            if tile.in_group('dig&cut_mark'):
                                self.dragging = -1
                            else:
                                self.dragging = 1
                        elif self.mode == 'resource' and tile and tile.in_group('earth'):
                            if tile.in_group('resource_mark'):
                                self.dragging = -1
                            else:
                                self.dragging = 1
                        elif self.mode == 'torch':
                            if isinstance(tile, BgTile):
                                BuildMark(self.map, tile.pos, 'torch')
                            elif isinstance(tile, Torch):
                                tile.kill()
                        elif self.mode == 'remove' and tile is not None:
                            tile.kill()
                if e.button == 3:
                    self.dragging_camera = True
                if e.button == 4:
                    self.mode = self.modes[(self.modes.index(self.mode) - 1) % len(self.modes)]
                    self.snd['shift'].play()
                if e.button == 5:
                    self.mode = self.modes[(self.modes.index(self.mode) + 1) % len(self.modes)]
                    self.snd['shift'].play()
            # ----- 鼠标按下事件 -----

            # ----- 鼠标放开事件 -----
            if e.type == pg.MOUSEBUTTONUP:
                if e.button == 1:
                    if self.dragging:
                        self.dragging = False
                if e.button == 2:  # debug
                    pass
                if e.button == 3:
                    self.dragging_camera = False
            # ----- 鼠标放开事件 -----

            # ----- 键盘按下事件 -----
            if e.type == pg.KEYDOWN:
                if e.key == pg.K_SPACE:
                    self.pause = False if self.pause else True
                if e.key == pg.K_1:
                    self.game_speed = 800
                if e.key == pg.K_2:
                    self.game_speed = 600
                if e.key == pg.K_3:
                    self.game_speed = 400
                if e.key == pg.K_4:
                    self.game_speed = 200
                if e.key == pg.K_z:
                    if config.TILESIZE == 48:
                        config.TILESIZE = 32
                        self.camera.offset += (self.cursor_pos.x * 16, self.cursor_pos.y * 16)
                    else:
                        config.TILESIZE = 48
                        self.camera.offset -= (self.cursor_pos.x * 16, self.cursor_pos.y * 16)
                    self.camera.repair()
                if e.key == pg.K_d:
                    self.mode = 'dig&cut'
                if e.key == pg.K_i:
                    self.mode = 'imp'
                if e.key == pg.K_l:
                    self.mode = 'ladder'
                if e.key == pg.K_r:
                    self.mode = 'resource'
                if e.key == pg.K_c:
                    self.mode = 'torch'
            # ----- 键盘按下事件 -----

    def draw(self):
        # draw debug HUD
        pg.display.set_caption("{:.2f}".format(self.clock.get_fps()))
        # pg.display.set_caption("camera({}, {})".format(self.camera.offset.x, self.camera.offset.y))
        # pg.display.set_caption(
        #     "({},{},{})".format(self.cursor_pos.x, self.cursor_pos.y,
        #     (type(self.map.data[vec2int(self.cursor_pos)]))))

        self.screen.blit(pg.transform.scale(self.img['sky_top'], (WIDTH, 100)), (0, 0))
        self.screen.blit(self.img['sky'], (0, 100))
        self.screen.blit(self.img['sky'], (512, 100))
        self.screen.blit(pg.transform.scale(self.img['sky_bottom'], (WIDTH, 512)), (0, 612))

        tiles = self.map.draw(self.camera)
        # pg.display.set_caption(str(tiles))
        # self.all_sprites.draw(self.screen)
        for sprite in self.all_sprites:
            if isinstance(sprite, Wood) and sprite.owner:  # 隐藏被捡起来的木头
                continue
            self.screen.blit(sprite.image, self.camera.apply(sprite))

        # draw target box and mouse cursor
        target = pg.Rect(self.cursor_pos.x * config.TILESIZE + self.camera.offset.x,
                         self.cursor_pos.y * config.TILESIZE + self.camera.offset.y,
                         config.TILESIZE, config.TILESIZE)
        pg.draw.rect(self.screen, WHITE, target, 2)

        self.draw_mode_icon(self.mode)
        # draw game speed
        if self.pause:
            self.draw_text('PAUSE', 32, RED, vec(WIDTH / 2, 16), align='mid')
        else:
            self.draw_text('SPEED:', 32, WHITE, vec(WIDTH / 2 - 130, 16), align='mid')
            for i in range(1, 5):
                if 1000 - (200 * i) == self.game_speed:
                    self.draw_text('x' + str(i), 38, BROWN, vec(WIDTH / 2 - 100 + 56 * i, 16), align='mid')
                else:
                    self.draw_text('x' + str(i), 32, WHITE, vec(WIDTH / 2 - 100 + 56 * i, 16), align='mid')
        # draw resource
        # count woods
        self.resource['woods'] = 0
        for wood in self.woods:
            if vec2int(wood.pos + vec(0, 1)) in self.map.groups['resource_mark']:
                self.resource['woods'] += 1
        count_woods = self.resource['woods']
        for bm in self.map.groups['build_mark']:
            bm = self.map.data[bm]
            if bm.image_name == 'ladder':
                count_woods -= 1
            elif bm.image_name == 'shelf':
                count_woods -= 3
            elif bm.image_name == 'bed':
                count_woods -= 4
        self.screen.blit(pg.transform.scale(self.img['wood'], (24, 24)), (16, HEIGHT - 30))
        if count_woods >= 0:
            self.draw_text('x' + str(count_woods), 24, WHITE, (40, HEIGHT - 24))
        else:
            self.draw_text('x' + str(count_woods), 24, RED, (40, HEIGHT - 24))
        self.screen.blit(self.img['cursor'], self.last_mouse_pos - (15, 10))
        pg.display.flip()

    def draw_mode_icon(self, mode):
        if mode == 'dig&cut':
            image = self.img['axe_iron']
            mode_name = 'Dig&Cut'
        elif mode == 'resource':
            image = self.map.image['greystone_sand']
            mode_name = 'Set Resource Area'
        elif mode == 'imp':
            image = self.img['imp']
            mode_name = 'Minion'
        elif mode == 'ladder':
            image = self.map.image['ladder'].copy()
            mode_name = 'Ladder'
        elif mode == 'torch':
            image = self.map.image['torch']
            mode_name = 'Torch'
        elif mode == 'shelf':
            image = self.map.image['shelf']
            mode_name = 'Library'
        elif mode == 'bed':
            image = self.map.image['bed']
            mode_name = 'Bed'
        else:
            image = self.map.image['table']
            mode_name = 'Nothing'
        self.screen.blit(pg.transform.scale(image, (64, 64)), vec(WIDTH - 96, HEIGHT - 96))
        self.draw_text(mode_name, 46, WHITE, vec(WIDTH - 104, HEIGHT - 90), align='right')

    def draw_text(self, text, font_size, color, pos, align='left'):
        font = pg.font.Font(self.font_name, font_size)
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect()
        if align == 'left':
            text_rect.topleft = pos
        elif align == 'mid':
            text_rect.midtop = pos
        elif align == 'right':
            text_rect.topright = pos
        self.screen.blit(text_surface, text_rect)

    def zoom(self, n):
        config.TILESIZE += n
        if 32 <= config.TILESIZE <= 96:
            self.camera.offset -= (self.cursor_pos.x * n, self.cursor_pos.y * n)
        config.TILESIZE = max(32, config.TILESIZE)
        config.TILESIZE = min(96, config.TILESIZE)

        self.camera.repair()

if __name__ == '__main__':
    g = Game()
    while g.running:
        g.new()
        g.run()

    pg.quit()
