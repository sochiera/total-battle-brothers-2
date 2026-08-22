"""Original procedural 2D art for Total Battle Brothers.

Sprites are painted with pixel noise, dithering and silhouettes at import
time - no copyrighted image files, and noticeably richer than flat
rectangles: dithered terrain, tree silhouettes, gabled houses, castles,
spear/bow/armour unit marks and parchment UI panels.
"""
import random

import pygame

from ..rules import constants as C

_TRANSPARENT = (0, 0, 0, 0)


def _px(surf, x, y, color):
    if 0 <= x < surf.get_width() and 0 <= y < surf.get_height():
        surf.set_at((x, y), color)


def _fuzzy(rng, color, db=12):
    d = rng.randint(-db, db)
    return tuple(max(0, min(255, c + d)) for c in color)


def _new(w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    return s


# ------------------------------------------------------------------ terrain
def _grass_tile(seed, base=(96, 118, 74)):
    rng = random.Random(seed)
    s = _new(24, 24)
    for y in range(24):
        for x in range(24):
            c = _fuzzy(rng, base, 6)
            _px(s, x, y, c)
    for _ in range(16):
        sx, sy = rng.randint(0, 23), rng.randint(0, 23)
        c = _fuzzy(rng, base, 22)
        _px(s, sx, sy, c)
    # tufts
    for _ in range(4):
        sx, sy = rng.randint(2, 20), rng.randint(2, 20)
        _px(s, sx, sy, (70, 96, 50))
        _px(s, sx + 1, sy, (70, 96, 50))
        _px(s, sx, sy + 1, (70, 96, 50))
    return s


def terrain_sprites():
    sp = {}
    sp[C.TERRAIN_PLAINS] = _grass_tile(1)
    sp[C.TERRAIN_FOREST] = woods_tile(2)
    sp[C.TERRAIN_HILLS] = hill_tile(3)
    sp[C.TERRAIN_RIVER] = river_tile(4)
    sp[(C.TERRAIN_RIVER, "ford")] = crossing_tile(8, "ford")
    sp[(C.TERRAIN_RIVER, "bridge")] = crossing_tile(9, "bridge")
    sp[C.TERRAIN_ROAD] = road_tile(5)
    sp[C.TERRAIN_RUINS] = ruins_tile(6)
    sp[C.TERRAIN_VILLAGE] = village_tile(7)
    return sp


def road_tile(seed):
    s = _grass_tile(seed, (102, 112, 72))
    for y in range(9, 15):
        for x in range(24):
            _px(s, x, y, (122, 92, 62) if (x + y) % 5 else (92, 70, 52))
    return s


def crossing_tile(seed, kind):
    s = river_tile(seed)
    colour = (186, 151, 92) if kind == "ford" else (92, 62, 42)
    for y in range(9, 15):
        for x in range(24):
            if kind == "ford" or x % 4 != 0:
                _px(s, x, y, colour)
    return s


def village_tile(seed):
    base = _grass_tile(seed, (90, 108, 66))
    rng = random.Random(seed + 5)
    for _ in range(6):
        hx, hy = rng.randint(2, 18), rng.randint(6, 17)
        for y in range(3):
            for x in range(4):
                _px(base, hx + x, hy + y, (128, 88, 54))
        for x in range(6):
            _px(base, hx + x - 1, hy - 1, (98, 46, 40))
    return base


def woods_tile(seed):
    rng = random.Random(seed)
    base = _grass_tile(seed, (88, 102, 62))
    for _ in range(9):
        tx, ty = rng.randint(2, 18), rng.randint(4, 18)
        hgt = rng.randint(3, 6)
        for yy in range(hgt):
            w = hgt - yy
            colour = (36, 54, 26) if yy < hgt - 2 else (52, 78, 38)
            for xx in range(-w, w + 1):
                _px(base, tx + xx, ty + yy, colour)
        _px(base, tx, ty + hgt, (70, 48, 30))  # trunk
        _px(base, tx + 1, ty + hgt, (70, 48, 30))
    return base


def hill_tile(seed):
    rng = random.Random(seed)
    base = _grass_tile(seed, (112, 108, 78))
    for _ in range(5):
        cx, cy = rng.randint(6, 18), rng.randint(5, 14)
        rad = rng.randint(3, 5)
        for yy in range(-rad, rad):
            for xx in range(-rad, rad):
                if xx * xx + yy * yy <= rad * rad:
                    shade = 0 if (-xx + yy) > rad // 2 else 40
                    c = (92 + shade, 86 + shade, 56 + shade)
                    _px(base, cx + xx, cy + yy, c)
    # ridge highlight lines
    for x in range(3, 21):
        _px(base, x, 6 if x % 2 else 7, (140, 138, 100))
    return base


def river_tile(seed):
    rng = random.Random(seed)
    s = _new(24, 24)
    for y in range(24):
        for x in range(24):
            c = _fuzzy(rng, (86, 96, 122), 8)
            _px(s, x, y, c)
    for yy in range(0, 24, 4):
        for xx in range(24):
            _px(s, xx, yy, (150, 170, 210))
    return s


def ruins_tile(seed):
    rng = random.Random(seed)
    s = _new(24, 24)
    for y in range(24):
        for x in range(24):
            c = _fuzzy(rng, (140, 116, 78), 10)
            _px(s, x, y, c)
    for _ in range(12):
        _px(s, rng.randint(0, 23), rng.randint(0, 23), (168, 140, 96))
    return s


# ----------------------------------------------------------------- settlement
def settlement_sprite(size, owner_colour):
    if size == C.SIZE_V:
        return village_sprite(owner_colour)
    if size == C.SIZE_T:
        return town_sprite(owner_colour)
    return city_sprite(owner_colour)


def village_sprite(col):
    s = _new(26, 24)
    # huts
    for hx in (4, 12, 18):
        w = rng_ish(hx)
        for y in range(3):
            for x in range(4):
                _px(s, hx + x, 8 + y, (122, 84, 52))
        for x in range(4):
            _px(s, hx + x, 7, (140, 100, 62))
        # roof
        for x in range(6):
            _px(s, hx + x - 1, 6, (96, 44, 40))
        for x in range(4):
            _px(s, hx + x, 5, (96, 44, 40))
    return s


def rng_ish(n):
    return (n * 37) % 5


def town_sprite(col):
    s = _new(28, 28)
    village_sprite(col)
    # palisade
    for x in range(2, 25):
        _px(s, x, 19, (122, 96, 62))
        _px(s, x, 20, (122, 96, 62))
    for x in range(2, 25, 3):
        _px(s, x, 20, (88, 66, 44))
    # a tower
    for y in range(12, 19):
        for x in range(6, 9):
            _px(s, x, y, (140, 128, 108))
    for x in range(5, 10):
        _px(s, x, 11, (70, 56, 40))
    return s


def city_sprite(col):
    s = _new(30, 30)
    # keep
    for y in range(8, 22):
        for x in range(10, 18):
            _px(s, x, y, (150, 132, 110))
    for x in range(8, 20):
        _px(s, x, 8, (80, 62, 44))
    for x in range(9, 19):
        _px(s, x, 7, (80, 62, 44))
    # towers
    for (tx, ty) in ((4, 12), (20, 12)):
        for y in range(ty - 6, ty + 6):
            for x in range(tx, tx + 4):
                _px(s, x, y, (140, 118, 96))
    # banners in owner colour
    for bx in (6, 20):
        for y in range(7, 11):
            _px(s, bx, y, col)
    return s


def _apply(s, fn_base):
    pass


# --------------------------------------------------------------- UI chrome
def parchment(w, h, base=(228, 208, 164)):
    s = _new(w, h)
    rng = random.Random(7)
    for y in range(h):
        for x in range(w):
            c = _fuzzy(rng, base, 6)
            if x < 2 or y < 2 or x >= w - 2 or y >= h - 2:
                c = (84, 54, 30)
            _px(s, x, y, c)
    return s


def button_sprite(text, font, w=180, h=30):
    s = _new(w, h)
    for y in range(h):
        for x in range(w):
            if x < 1 or y < 1 or x >= w - 1 or y >= h - 1:
                c = (56, 36, 22)
            elif y < 4:
                c = (150, 108, 66)
            else:
                c = (188, 140, 92)
            _px(s, x, y, c)
    s.blit(font.render(text, True, (30, 20, 12)), (8, 6))
    return s


# ------------------------------------------------------------------ units
def unit_sprite(colour, kit, hero=False):
    s = _new(16, 20)
    # body cloak
    body = tuple(max(0, c - 20) for c in colour)
    for y in range(9, 17):
        for x in range(5, 11):
            _px(s, x, y, body)
    # legs
    for x in range(6, 9):
        _px(s, x, 16, body)
        _px(s, x, 17, body)
        _px(s, x + 1, 17, body)
    # head
    hel = (150, 155, 160) if hero else (120, 122, 126)
    for y in range(5, 9):
        for x in range(6, 10):
            _px(s, x, y, hel)
    # helmet plume for heroes
    if hero:
        for y in range(2, 6):
            _px(s, 7, y, colour)
        _px(s, 8, 3, colour)
    # shield
    if "shield" in kit or "heavy" in kit:
        for y in range(9, 15):
            for x in range(1, 4):
                _px(s, x, y, (90, 40, 36))
        _px(s, 1, 11, (70, 30, 28))
    # weapon
    if kit in ("bow", "heavy_bow"):
        for y in range(5, 16):
            _px(s, 13, y, (104, 74, 40))
        _px(s, 12, 6, (80, 80, 80))
    elif kit in ("two_hand", "two_hander"):
        for y in range(6, 18):
            _px(s, 13, y, (150, 160, 168))
    else:
        for y in range(6, 14):
            _px(s, 12, y, (138, 148, 156))
    return s


def hero_banner(colour):
    s = _new(10, 14)
    for y in range(10):
        _px(s, 2, y, (90, 70, 45))
    for y in range(10):
        for x in range(3, 9):
            _px(s, x, y, colour)
    _px(s, 2, 10, (90, 70, 45))
    return s


def new(w, h):
    return _new(w, h)


def settlement_sprite_sheet(colors=((150, 40, 40), (35, 80, 160),
                                    (45, 120, 65), (155, 65, 15),
                                    (130, 120, 35))):
    sheet = {}
    for sector, col in enumerate(list(colors) + [(120, 60, 30)]):
        for size in C.SIZE_ORDER:
            sheet[(sector, size)] = settlement_sprite(size, col)
    return sheet


def unit_sprite_sheet(colors=((150, 40, 40), (35, 80, 160), (45, 120, 65),
                              (155, 65, 15), (130, 120, 35), (20, 20, 20))):
    sheet = {}
    for sector, col in enumerate(list(colors) + [(90, 90, 60)]):
        for kit in list(C.KITS):
            sheet[(sector, kit)] = unit_sprite(col, kit)
            sheet[(sector, kit, True)] = unit_sprite(col, kit, hero=True)
    return sheet


def bandit_sprite():
    """A separate road-raider silhouette, not a duchy-coloured unit."""
    s = _new(22, 26)
    cloak = (58, 35, 30)
    scarf = (166, 45, 28)
    metal = (156, 145, 122)
    for y in range(9, 22):
        width = 4 + (y - 9) // 4
        for x in range(11 - width, 11 + width):
            _px(s, x, y, cloak)
    for y in range(4, 9):
        for x in range(8, 14):
            _px(s, x, y, (112, 100, 86))
    for x in range(6, 16):
        _px(s, x, 8, scarf)
    for y in range(8, 21):
        _px(s, 18, y, metal)
    for x in range(16, 21):
        _px(s, x, 8, metal)
    return s
