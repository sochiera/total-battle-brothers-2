"""Small shared presentation helpers used by the screen classes."""
import math
from pathlib import Path

import pygame

TS = 22
SCREEN_W, SCREEN_H = 1280, 800
PANEL_W = 340
_CHROME = {}


def _chrome(name):
    if name not in _CHROME:
        try:
            path = Path(__file__).resolve().parents[2] / "assets" / "ui" / (name + ".png")
            _CHROME[name] = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            _CHROME[name] = False
    return _CHROME[name] or None


def hex_center(q, r, ox=0, oy=0, ts=TS):
    x = ox + ts * 1.72 * (q + r * 0.5)
    y = oy + ts * 1.5 * r
    return int(round(x)), int(round(y))


def pick_hex(px, py, ox=0, oy=0, ts=TS):
    x = (px - ox) / (ts * 1.72)
    y = (py - oy) / (ts * 1.5)
    qf = x - 0.5 * y
    rf = y
    sf = -qf - rf
    xr, yr, zr = round(qf), round(rf), round(sf)
    xdiff = abs(xr - qf)
    ydiff = abs(yr - rf)
    zdiff = abs(zr - sf)
    if xdiff > ydiff and xdiff > zdiff:
        xr = -yr - zr
    elif ydiff > zdiff:
        yr = -xr - zr
    return int(xr), int(yr)


def hex_corners(cx, cy, ts=TS):
    pts = []
    for i in range(6):
        ang = math.pi / 6 + i * math.pi / 3
        pts.append((cx + ts * 0.92 * math.cos(ang),
                    cy + ts * 0.92 * math.sin(ang)))
    return pts


def draw_panel(surf, x, y, w, h, title=None, font=None):
    pygame.draw.rect(surf, (218, 200, 158), (x, y, w, h))
    texture = _chrome("panel")
    if texture:
        for yy in range(y, y + h, texture.get_height()):
            for xx in range(x, x + w, texture.get_width()):
                surf.blit(texture, (xx, yy))
    pygame.draw.rect(surf, (92, 60, 34), (x, y, w, h), 3)
    for yy in range(y + 3, y + h - 3, 4):
        for xx in range(x + 3, x + w - 3, 7):
            shade = (198, 180, 140) if (((xx // 7) + (yy // 4)) % 2) else (
                222, 204, 162)
            surf.fill(shade, (xx, yy, 6, 3))
    if title:
        pygame.font.init()
        f = pygame.font.SysFont("dejavusans", 18)
        surf.blit(f.render(title, True, (44, 28, 14)), (x + 12, y + 8))


def draw_text(surf, font, text, x, y, colour=(30, 20, 12)):
    surf.blit(font.render(text, True, colour), (x, y))


class Button:
    def __init__(self, x, y, w, h, label, on_click, enabled=True):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.label = label
        self.on_click = on_click
        self.enabled = enabled
        self.rect = (x, y, w, h)

    def draw(self, surf, font):
        if not self.enabled:
            body, top, txt = (128, 118, 106), (138, 126, 112), (92, 84, 74)
        else:
            top, body, txt = (150, 108, 66), (188, 140, 92), (30, 20, 12)
        texture = _chrome("button")
        if texture:
            surf.blit(pygame.transform.scale(texture, (self.w, self.h)),
                      (self.x, self.y))
        else:
            pygame.draw.rect(surf, body, self.rect)
        pygame.draw.rect(surf, top, (self.x, self.y, self.w, 5))
        pygame.draw.rect(surf, (60, 38, 24), self.rect, 2)
        tw, th = font.size(self.label)
        surf.blit(font.render(self.label, True, txt),
                  (self.x + self.w // 2 - tw // 2,
                   self.y + self.h // 2 - th // 2))

    def hit(self, mx, my):
        return self.enabled and (self.x <= mx <= self.x + self.w and
                                 self.y <= my <= self.y + self.h)


def realm_index(campaign, realm_key):
    if realm_key is None:
        return 5
    return realm_key if realm_key in (0, 1, 2, 3, 4, 5) else 5
