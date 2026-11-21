#!/usr/bin/env python3
"""Saturday 21 November 2026, drawn as one newspaper front page.

A deterministic, standard-library-only Python 3.13 program. It paints a
1024x1024 PNG at /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png)
that sums up the world news of Saturday 21 November 2026: the overnight
Russian missile and drone barrage on Kyiv that also dropped ordnance in
Poland, the AI-led stock-market rout, the COP31 deadlock, and nine more
stories from six regions. Every headline and figure comes from reporting
published on 21 November 2026 (Reuters, AP, CNN, BBC, AFP, USGS and
others, listed in the footer).

The picture is drawn, not pasted: a hand-built 5x7 bitmap typeface, a
small rasteriser (rectangles, lines, circles, triangles, polygons) over
an RGB buffer, and a PNG writer built on zlib and struct. There is no
network access, no clock, no randomness, so the same source always
produces the same PNG bytes.

Layout, top to bottom: a navy masthead with the date, a full-width lead
story with a drawn night-sky scene over Kyiv, two half-width stories, a
row of three stories, a by-the-numbers strip, an also-today strip with
five more stories, and a sources footer.
"""

import os
import struct
import zlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Page geometry and palette
# ---------------------------------------------------------------------------
PAGE_W = 1024
PAGE_H = 1024
MARGIN = 28
CONTENT_W = PAGE_W - 2 * MARGIN

PAPER = (247, 243, 234)      # warm newsprint
INK = (18, 18, 20)           # near-black type
NAVY = (24, 38, 74)          # masthead band
NAVY_LT = (44, 62, 108)      # lighter navy for scenes
RED = (168, 31, 31)          # accent red
GOLD = (214, 164, 65)        # warm gold for explosions / numbers
GREY = (108, 104, 96)        # secondary type
RULE = (60, 56, 50)          # thin rules
SKY = (13, 20, 38)           # night sky in the lead scene
AMBER = (232, 148, 42)       # fire / explosion amber
SMOKE = (120, 122, 132)      # smoke grey
GREEN = (32, 110, 62)        # small positive accent
WHITE = (250, 248, 242)

# ---------------------------------------------------------------------------
# Stories of the day (all reported on 21 November 2026)
# ---------------------------------------------------------------------------
MASTHEAD = "THE WORLD IN ONE DAY"
DATE_LINE = "SATURDAY 21 NOVEMBER 2026"
DATE_TAG = "12 STORIES  -  6 REGIONS"

LEAD = {
    "kicker": "KYIV  |  WAR IN UKRAINE",
    "headline": "RUSSIA'S BIGGEST STRIKE HITS KYIV - MISSILES LAND IN POLAND",
    "summary": (
        "RUSSIA FIRED MORE THAN 400 DRONES AND 110 MISSILES AT UKRAINE "
        "OVERNIGHT. AT LEAST 8 PEOPLE WERE KILLED IN KYIV AS STRIKES "
        "DAMAGED BRIDGES AND RAILWAY STATIONS. POLAND SAID TWO MISSILES "
        "AND A SUSPECTED DRONE CAME DOWN ON ITS SOIL, AND PRIME MINISTER "
        "TUSK CALLED IT A DELIBERATE PROVOCATION."
    ),
}

HALF_STORIES = [
    {
        "kicker": "NEW YORK  |  MARKETS",
        "headline": "AI ROUT DRAGS S&P 500 INTO CORRECTION",
        "summary": (
            "US STOCKS FELL 3.7% AS AN AI AND CHIP SELL-OFF SPREAD. THE "
            "NASDAQ LOST 5.28% AND TOKYO'S NIKKEI 5.06%."
        ),
        "scene": "chart",
    },
    {
        "kicker": "ANTALYA  |  CLIMATE",
        "headline": "COP31 DEADLOCK OVER FOSSIL FUELS",
        "summary": (
            "THE UN CLIMATE SUMMIT RAN PAST ITS DEADLINE AS NEARLY 200 "
            "NATIONS FAILED TO AGREE ON FOSSIL FUELS."
        ),
        "scene": "globe",
    },
]

THIRD_STORIES = [
    {
        "kicker": "WASHINGTON  |  CYBER",
        "headline": "FBI CRIMINAL DATABASE HACKED",
        "summary": (
            "THE FBI IS INVESTIGATING AN APPARENT HACK OF ITS CRIMINAL "
            "DATABASE AS US COMPUTER OUTAGES CONTINUE."
        ),
        "scene": "screen",
    },
    {
        "kicker": "PERU  |  EARTHQUAKE",
        "headline": "6.9 QUAKE SHAKES PERU'S ANDES",
        "summary": (
            "THE TREMOR STRUCK AT 00:09 GMT, WAS FELT IN LIMA, AND LEFT "
            "NO CASUALTIES REPORTED, PERU'S INSTITUTE SAID."
        ),
        "scene": "quake",
    },
    {
        "kicker": "BASRA  |  IRAQ",
        "headline": "POWER PLANT FIRE KILLS 4",
        "summary": (
            "A FIRE AT THE HARTHA THERMAL POWER STATION KILLED AT LEAST "
            "FOUR PEOPLE AND INJURED 35, OFFICIALS SAID."
        ),
        "scene": "fire",
    },
]

NUMBERS = "BY THE NUMBERS: 400+ DRONES - 110 MISSILES - S&P -3.7% - $7.25BN - 6.9 - $2TN"

ALSO = [
    ("TECH", "ANTHROPIC DEBUTS AT $2TN ON WALL STREET"),
    ("LOS ANGELES", "PALISADES FIRE: MAN CONVICTED"),
    ("BRUSSELS", "UK-EU SIGN 3 POST-BREXIT DEALS"),
    ("EUROPE", "GEN Z PROTESTS IN 25 NATIONS"),
    ("GULF", "IRAN: US MQ-9 DRONE DOWNED"),
]

FOOTER = (
    "SOURCES: REUTERS, AP, CNN, BBC, AFP, USGS, NYT  -  ALL EVENTS HAPPENED OR WERE "
    "FIRST REPORTED ON SATURDAY 21 NOVEMBER 2026."
)

# ---------------------------------------------------------------------------
# Canvas: an RGB buffer with simple drawing primitives
# ---------------------------------------------------------------------------
class Canvas:
    def __init__(self, width, height, colour):
        self.w = width
        self.h = height
        self.buf = bytearray(colour * (width * height))

    def put(self, x, y, colour):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i] = colour[0]
            self.buf[i + 1] = colour[1]
            self.buf[i + 2] = colour[2]

    def rect(self, x, y, w, h, colour):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(colour) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.buf[i:i + (x1 - x0) * 3] = row

    def hline(self, x, y, w, colour, thick=1):
        self.rect(x, y, w, thick, colour)

    def vline(self, x, y, h, colour, thick=1):
        self.rect(x, y, thick, h, colour)

    def line(self, x0, y0, x1, y1, colour):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.put(x, y, colour)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def circle(self, cx, cy, r, colour, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy)
                if fill:
                    if d2 <= r * r:
                        self.put(xx, yy, colour)
                else:
                    if r * r - 2 * r <= d2 <= r * r:
                        self.put(xx, yy, colour)

    def ring(self, cx, cy, r, colour, thick=2):
        for t in range(thick):
            self.circle(cx, cy, r - t, colour, fill=False)

    def triangle(self, x0, y0, x1, y1, x2, y2, colour):
        # Scanline fill of a triangle.
        pts = sorted([(x0, y0), (x1, y1), (x2, y2)], key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = pts
        if ay == cy:
            return
        def edge(xa, ya, xb, yb, y):
            if yb == ya:
                return xa
            return xa + (xb - xa) * (y - ya) / (yb - ya)
        for y in range(ay, cy + 1):
            if y < by:
                xl = edge(ax, ay, bx, by, y)
                xr = edge(ax, ay, cx, cy, y)
            else:
                xl = edge(bx, by, cx, cy, y)
                xr = edge(ax, ay, cx, cy, y)
            if xl > xr:
                xl, xr = xr, xl
            self.rect(int(xl), y, int(xr) - int(xl) + 1, 1, colour)

    def starburst(self, cx, cy, r, colour, rays=10):
        import math
        for k in range(rays):
            a = 2 * math.pi * k / rays
            x1 = int(cx + r * math.cos(a))
            y1 = int(cy + r * math.sin(a))
            self.line(cx, cy, x1, y1, colour)
        self.circle(cx, cy, max(2, r // 3), colour)

# ---------------------------------------------------------------------------
# PNG writer (colour type 2, 8-bit, no filtering)
# ---------------------------------------------------------------------------
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out

def write_png(canvas, path):
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)
        raw.extend(canvas.buf[y * stride:(y + 1) * stride])
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(png)
    return len(png)

# ---------------------------------------------------------------------------
# 5x7 bitmap typeface, drawn by hand for this page.
# Each glyph is seven rows of five cells; '#' is ink, '.' is blank.
# ---------------------------------------------------------------------------
GLYPHS = {
    "A": ("..#..", ".#.#.", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "..##.", ".#...", "#....", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "/": ("....#", "...#.", "...#.", "..#..", ".#...", "#....", "#...."),
    "|": ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "%": ("#...#", "#..#.", "...#.", "..#..", ".#...", "#..#.", "#...#"),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "&": (".###.", "#...#", "#...#", ".#...", "#.#.#", "#..#.", ".##.#"),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "*": (".....", ".....", ".###.", ".###.", ".###.", ".....", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "<": ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    ">": (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
}

def text_width(text, scale):
    """Width in pixels of text at the given scale (6 cells per glyph)."""
    return len(text) * 6 * scale - scale

def draw_text(cv, x, y, text, scale, colour):
    """Draw one line of (uppercased) text; returns the x of its end."""
    cx = x
    for ch in text.upper():
        glyph = GLYPHS.get(ch, GLYPHS["?"])
        for row_i, row in enumerate(glyph):
            for col_i, cell in enumerate(row):
                if cell == "#":
                    cv.rect(cx + col_i * scale, y + row_i * scale,
                            scale, scale, colour)
        cx += 6 * scale
    return cx - scale

def draw_text_centred(cv, cx, y, text, scale, colour):
    w = text_width(text, scale)
    draw_text(cv, cx - w // 2, y, text, scale, colour)

def wrap_text(text, max_width, scale):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    limit = max(1, max_width // (6 * scale))
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        cur = ""
        for word in words:
            trial = (cur + " " + word).strip()
            if len(trial) <= limit:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines

def draw_block(cv, x, y, max_width, text, scale, colour, leading=None):
    """Draw wrapped text; returns the y just below the last line."""
    if leading is None:
        leading = 7 * scale + 4
    for line in wrap_text(text, max_width, scale):
        draw_text(cv, x, y, line, scale, colour)
        y += leading
    return y

def kicker_bar(cv, x, y, text, scale, colour):
    """A small red bar followed by a kicker line."""
    cv.rect(x, y, 4 * scale, 7 * scale, colour)
    draw_text(cv, x + 6 * scale, y, text, scale, colour)

# ---------------------------------------------------------------------------
# Drawn scenes (no photos: every panel is painted with the primitives)
# ---------------------------------------------------------------------------
def scene_kyiv(cv, x, y, w, h):
    """Night sky over a city skyline: missile streaks, bursts, smoke."""
    cv.rect(x, y, w, h, SKY)
    # Stars.
    stars = [(12, 14), (46, 30), (88, 10), (130, 26), (170, 12), (205, 34),
             (240, 16), (280, 28), (310, 10), (70, 44), (150, 48), (255, 46)]
    for sx, sy in stars:
        if sx < w and sy < h:
            cv.put(x + sx, y + sy, WHITE)
            cv.put(x + sx + 1, y + sy, WHITE)
    # Moon.
    cv.circle(x + w - 52, y + 40, 16, (232, 226, 200))
    cv.circle(x + w - 58, y + 36, 13, SKY)
    # Missile streaks with bright heads.
    streaks = [(30, 120, 150, 40), (90, 150, 210, 60), (170, 140, 280, 55),
               (230, 165, 320, 90)]
    for x0, y0, x1, y1 in streaks:
        cv.line(x + x0, y + y0, x + x1, y + y1, GOLD)
        cv.circle(x + x1, y + y1, 4, AMBER)
        cv.circle(x + x1, y + y1, 2, WHITE)
    # Explosion bursts.
    cv.starburst(x + 70, y + 95, 26, AMBER, rays=12)
    cv.circle(x + 70, y + 95, 9, GOLD)
    cv.starburst(x + 250, y + 120, 20, GOLD, rays=10)
    cv.circle(x + 250, y + 120, 7, AMBER)
    # Smoke columns.
    for sx, sy, r in [(64, 78, 12), (74, 62, 16), (244, 104, 11), (252, 88, 14)]:
        cv.circle(x + sx, y + sy, r, SMOKE)
    # Skyline silhouettes with a few lit windows.
    base = y + h
    buildings = [(0, 150, 46, 150), (50, 120, 40, 180), (94, 165, 52, 135),
                 (150, 110, 44, 190), (198, 150, 48, 150), (250, 125, 42, 175),
                 (296, 160, 40, 140)]
    for bx, bh, bw, _ in buildings:
        cv.rect(x + bx, base - bh, bw, bh, (8, 11, 22))
    windows = [(58, 40), (104, 60), (160, 30), (206, 55), (258, 45),
               (306, 70), (112, 100), (168, 80), (264, 95)]
    for wx, wy in windows:
        cv.rect(x + wx, base - wy, 5, 6, GOLD)
    # Ground line.
    cv.hline(x, base - 2, w, (8, 11, 22), 2)

def scene_chart(cv, x, y, w, h):
    """A falling market chart: red bars stepping down, arrow, axis."""
    cv.rect(x, y, w, h, (238, 232, 220))
    # Frame.
    cv.hline(x, y + h - 22, w, RULE, 2)
    cv.vline(x + 14, y + 8, h - 30, RULE, 2)
    bars = [88, 78, 82, 66, 70, 54, 58, 42, 32]
    bw = (w - 34) // len(bars)
    for i, bh in enumerate(bars):
        bx = x + 20 + i * bw
        cv.rect(bx + 3, y + h - 24 - bh, bw - 6, bh, RED)
    # Downward arrow over the bars.
    cv.line(x + 22, y + 26, x + w - 24, y + h - 44, RED)
    cv.line(x + w - 24, y + h - 44, x + w - 46, y + h - 48, RED)
    cv.line(x + w - 24, y + h - 44, x + w - 28, y + h - 66, RED)
    draw_text(cv, x + 20, y + 6, "-3.7%", 2, RED)

def scene_globe(cv, x, y, w, h):
    """A globe over a cracked dry earth line: climate talks."""
    cv.rect(x, y, w, h, (222, 232, 226))
    cx, cy, r = x + w // 2, y + h // 2 - 6, 58
    cv.circle(cx, cy, r, (52, 110, 158))
    # Continents as simple blobs.
    cv.circle(cx - 22, cy - 14, 14, GREEN)
    cv.circle(cx + 18, cy + 8, 16, GREEN)
    cv.circle(cx + 24, cy - 22, 9, GREEN)
    cv.circle(cx - 26, cy + 22, 8, GREEN)
    # Latitude rings.
    cv.ring(cx, cy, r, (250, 248, 242), 2)
    cv.line(cx - r, cy, cx + r, cy, (250, 248, 242))
    cv.line(cx - r + 18, cy - 34, cx + r - 18, cy - 34, (250, 248, 242))
    cv.line(cx - r + 18, cy + 34, cx + r - 18, cy + 34, (250, 248, 242))
    # Sun with rays, top right.
    sx, sy = x + w - 34, y + 26
    cv.circle(sx, sy, 12, AMBER)
    cv.starburst(sx, sy, 22, AMBER, rays=8)
    # Cracked ground line.
    gy = y + h - 16
    cv.hline(x + 10, gy, w - 20, (120, 96, 60), 3)
    cv.line(x + w // 3, gy, x + w // 3 + 12, gy + 10, (120, 96, 60))
    cv.line(x + 2 * w // 3, gy, x + 2 * w // 3 - 10, gy + 10, (120, 96, 60))

def scene_screen(cv, x, y, w, h):
    """A monitor with a padlock and a warning badge: a hack."""
    cv.rect(x, y, w, h, (228, 230, 236))
    mx, my, mw, mh = x + 26, y + 14, w - 52, h - 44
    cv.rect(mx, my, mw, mh, NAVY)
    cv.rect(mx + 4, my + 4, mw - 8, mh - 8, (14, 22, 44))
    # Code lines.
    for i, lw in enumerate([64, 92, 48, 76]):
        cv.rect(mx + 14, my + 12 + i * 11, lw, 4, (84, 150, 110))
    # Padlock, bottom right inside the monitor.
    lx, ly = mx + mw - 62, my + mh - 36
    cv.rect(lx, ly, 44, 34, GOLD)
    cv.rect(lx + 8, ly - 14, 28, 16, GOLD)
    cv.rect(lx + 18, ly + 10, 8, 12, NAVY)
    cv.circle(lx + 22, ly + 8, 5, NAVY)
    # Red warning badge, top right inside the monitor.
    bx, by = mx + mw - 18, my + 16
    cv.circle(bx, by, 10, RED)
    draw_text(cv, bx - 3, by - 3, "!", 1, WHITE)
    # Stand.
    cv.rect(x + w // 2 - 4, my + mh, 8, 12, NAVY)
    cv.rect(x + w // 2 - 26, my + mh + 12, 52, 5, NAVY)

def scene_quake(cv, x, y, w, h):
    """Andes ridges split by a jagged crack, with a seismograph trace."""
    cv.rect(x, y, w, h, (226, 220, 206))
    base = y + h - 34
    # Mountain ridges.
    cv.triangle(x + 4, base, x + 70, y + 34, x + 136, base, (96, 104, 116))
    cv.triangle(x + 90, base, x + 160, y + 18, x + 230, base, (70, 78, 94))
    cv.triangle(x + 170, base, x + 236, y + 52, x + w - 4, base, (110, 118, 130))
    # Snow caps.
    cv.triangle(x + 58, y + 44, x + 70, y + 34, x + 82, y + 44, WHITE)
    cv.triangle(x + 148, y + 28, x + 160, y + 18, x + 172, y + 28, WHITE)
    # Jagged crack down the middle ridge.
    cx = x + 150
    cv.line(cx, y + 30, cx - 8, y + 60, INK)
    cv.line(cx - 8, y + 60, cx + 6, y + 92, INK)
    cv.line(cx + 6, y + 92, cx - 6, y + 124, INK)
    cv.line(cx - 6, y + 124, cx + 4, base, INK)
    # Seismograph strip.
    sy = y + h - 22
    cv.rect(x + 8, sy, w - 16, 16, WHITE)
    pts = [0, 2, -2, 3, -4, 6, -8, 10, -12, 8, -4, 2, -1, 1, 0]
    px = x + 12
    for v in pts:
        cv.vline(px, sy + 8 + v, 1, RED)
        px += (w - 28) // len(pts)
    draw_text(cv, x + 10, y + 8, "6.9", 3, RED)

def scene_fire(cv, x, y, w, h):
    """Flames rising from a power plant, with smoke and a tower."""
    cv.rect(x, y, w, h, (240, 228, 210))
    base = y + h - 20
    # Cooling tower silhouette.
    cv.rect(x + 22, y + 46, 44, base - y - 46, (140, 134, 124))
    cv.rect(x + 18, y + 40, 52, 8, (120, 114, 104))
    # Chimney.
    cv.rect(x + w - 52, y + 30, 20, base - y - 30, (120, 114, 104))
    # Smoke puffs.
    for sx, sy, r in [(x + w - 42, y + 16, 9), (x + w - 28, y + 6, 11),
                      (x + 60, y + 34, 8)]:
        cv.circle(sx, sy, r, SMOKE)
    # Flames: layered triangles and circles.
    fx = x + w // 2 + 30
    cv.triangle(fx - 34, base, fx, y + 48, fx + 34, base, AMBER)
    cv.triangle(fx - 22, base, fx, y + 72, fx + 22, base, GOLD)
    cv.circle(fx, base - 26, 14, (244, 120, 40))
    cv.circle(fx, base - 12, 8, (250, 210, 90))
    # Ground line.
    cv.hline(x, base, w, RULE, 2)
    draw_text(cv, x + 10, y + 8, "4 DEAD - 35 HURT", 2, RED)

# ---------------------------------------------------------------------------
# Story cards
# ---------------------------------------------------------------------------
def draw_half_card(cv, x, y, w, h, story):
    cv.rect(x, y, w, h, PAPER)
    cv.rect(x, y, w, 3, RED)
    scene_w = 150
    scene_h = h - 18
    fn = {"chart": scene_chart, "globe": scene_globe}[story["scene"]]
    fn(cv, x + w - scene_w - 10, y + 9, scene_w, scene_h)
    tx = x + 12
    tw = w - scene_w - 34
    kicker_bar(cv, tx, y + 12, story["kicker"], 1, RED)
    yy = y + 12 + 7 + 10
    yy = draw_block(cv, tx, yy, tw, story["headline"], 2, INK, leading=18)
    draw_block(cv, tx, yy + 4, tw, story["summary"], 1, (52, 50, 46),
               leading=11)

def draw_third_card(cv, x, y, w, h, story):
    cv.rect(x, y, w, h, PAPER)
    cv.rect(x, y, w, 3, NAVY)
    scene_h = 96
    fn = {"screen": scene_screen, "quake": scene_quake,
          "fire": scene_fire}[story["scene"]]
    fn(cv, x + 10, y + 10, w - 20, scene_h)
    yy = y + 10 + scene_h + 8
    kicker_bar(cv, x + 10, yy, story["kicker"], 1, RED)
    yy += 7 + 8
    yy = draw_block(cv, x + 10, yy, w - 20, story["headline"], 2, INK,
                    leading=18)
    draw_block(cv, x + 10, yy + 4, w - 20, story["summary"], 1,
               (52, 50, 46), leading=11)

# ---------------------------------------------------------------------------
# Page assembly
# ---------------------------------------------------------------------------
def build_page():
    cv = Canvas(PAGE_W, PAGE_H, PAPER)
    x0 = MARGIN

    # ---- Masthead -------------------------------------------------------
    cv.rect(0, 0, PAGE_W, 8, NAVY)
    band_y = 16
    band_h = 128
    cv.rect(0, band_y, PAGE_W, band_h, NAVY)
    draw_text_centred(cv, PAGE_W // 2, band_y + 22, MASTHEAD, 5, WHITE)
    cv.hline(MARGIN, band_y + 74, CONTENT_W, GOLD, 3)
    # Date line: date on the left, story count on the right.
    draw_text(cv, x0, band_y + 88, DATE_LINE, 2, WHITE)
    tag_w = text_width(DATE_TAG, 2)
    draw_text(cv, PAGE_W - MARGIN - tag_w, band_y + 88, DATE_TAG, 2, GOLD)
    draw_text_centred(cv, PAGE_W // 2, band_y + 112,
                      "ONE DAY - THE WHOLE WORLD - IN ONE PICTURE", 1, (180, 188, 210))

    # ---- Lead story -----------------------------------------------------
    lead_y = 160
    lead_h = 272
    cv.rect(x0, lead_y, CONTENT_W, lead_h, PAPER)
    cv.rect(x0, lead_y, CONTENT_W, 4, RED)
    scene_w = 360
    scene_h = lead_h - 16
    scene_kyiv(cv, x0 + CONTENT_W - scene_w - 12, lead_y + 8, scene_w, scene_h)
    tx = x0 + 14
    tw = CONTENT_W - scene_w - 44
    kicker_bar(cv, tx, lead_y + 16, LEAD["kicker"], 2, RED)
    yy = lead_y + 16 + 14 + 14
    yy = draw_block(cv, tx, yy, tw, LEAD["headline"], 3, INK, leading=26)
    yy = draw_block(cv, tx, yy + 8, tw, LEAD["summary"], 2, (52, 50, 46),
                    leading=20)
    # Small dateline under the lead summary.
    draw_text(cv, tx, lead_y + lead_h - 26,
              "KYIV - WARSAW - REPORTED SATURDAY 21 NOVEMBER 2026", 1, GREY)

    # ---- Divider --------------------------------------------------------
    div_y = lead_y + lead_h + 14
    cv.hline(x0, div_y, CONTENT_W, RULE, 2)

    # ---- Two half-width stories ----------------------------------------
    half_y = div_y + 12
    half_h = 168
    half_w = (CONTENT_W - 16) // 2
    draw_half_card(cv, x0, half_y, half_w, half_h, HALF_STORIES[0])
    draw_half_card(cv, x0 + half_w + 16, half_y, half_w, half_h,
                   HALF_STORIES[1])

    # ---- Three third-width stories -------------------------------------
    third_y = half_y + half_h + 14
    third_h = 210
    third_w = (CONTENT_W - 2 * 14) // 3
    for i, story in enumerate(THIRD_STORIES):
        draw_third_card(cv, x0 + i * (third_w + 14), third_y, third_w,
                        third_h, story)

    # ---- By-the-numbers strip -----------------------------------------
    num_y = third_y + third_h + 14
    num_h = 44
    cv.rect(0, num_y, PAGE_W, num_h, NAVY)
    draw_text_centred(cv, PAGE_W // 2, num_y + 15, NUMBERS, 2, WHITE)

    # ---- Also today -----------------------------------------------------
    also_y = num_y + num_h + 12
    also_h = 58
    draw_text(cv, x0, also_y, "ALSO TODAY", 2, RED)
    cv.hline(x0, also_y + 20, CONTENT_W, RULE, 1)
    col_w = CONTENT_W // len(ALSO)
    for i, (place, headline) in enumerate(ALSO):
        cx = x0 + i * col_w
        if i:
            cv.vline(cx - 6, also_y + 26, also_h - 26, (200, 194, 182), 1)
        draw_text(cv, cx, also_y + 28, place, 1, GREY)
        draw_block(cv, cx, also_y + 40, col_w - 16, headline, 1, INK,
                   leading=11)

    # ---- Footer ---------------------------------------------------------
    foot_y = also_y + also_h + 8
    cv.hline(x0, foot_y, CONTENT_W, RULE, 2)
    draw_text_centred(cv, PAGE_W // 2, foot_y + 10, FOOTER, 1, GREY)

    return cv

def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    out_path = os.path.join(out_dir, "entry.png")
    page = build_page()
    size = write_png(page, out_path)
    print(f"wrote {out_path} ({size} bytes, {PAGE_W}x{PAGE_H})")

if __name__ == "__main__":
    main()
