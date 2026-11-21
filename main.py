# Velmara — Isles Above the Golden Sea
#
# A travel poster for a place that does not exist, drawn procedurally
# with the Python standard library only (no network, no image files).
#
# The program paints a 1024x1024 poster and writes it to
# /output/entry.png (or $POSTER_OUTPUT when set):
#
#   * a sunset sky over a golden sea,
#   * three floating terraced isles with waterfalls — the landmark
#     that makes Velmara a place you cannot find on any map,
#   * the invented place name VELMARA set large and legible across
#     the sky, with one short tagline and one invitation line.
#
# SPDX-License-Identifier: MIT

import binascii
import os
import struct
import zlib

W = 1024
H = 1024
OUT = os.environ.get("POSTER_OUTPUT", "/output/entry.png")

# ---------------------------------------------------------------- canvas

# The picture is one flat RGB bytearray.  Everything is drawn with
# horizontal spans, which keeps a million-pixel painting fast in
# plain Python: a span is a single slice assignment.
canvas = bytearray(W * H * 3)


def rgb(r, g, b):
    return bytes((r, g, b))


def lerp(a, b, t):
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def span(y, x0, x1, color):
    """Fill pixels [x0, x1) on row y with a solid colour."""
    if y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W, x1)
    if x1 <= x0:
        return
    base = (y * W + x0) * 3
    canvas[base:base + (x1 - x0) * 3] = color * (x1 - x0)


def rect(x, y, w, h, color):
    for yy in range(y, y + h):
        span(yy, x, x + w, color)


def disc(cx, cy, r, color):
    """Filled circle, drawn row by row."""
    r2 = r * r
    for y in range(cy - r, cy + r + 1):
        dy = y - cy
        dx = int((r2 - dy * dy) ** 0.5)
        span(y, cx - dx, cx + dx + 1, color)


def ellipse(cx, cy, rx, ry, color):
    for y in range(cy - ry, cy + ry + 1):
        dy = (y - cy) / ry
        dx = int(rx * (1 - dy * dy) ** 0.5)
        span(y, cx - dx, cx + dx + 1, color)


def poly_rows(points, color):
    """Fill a simple polygon given as [(x, y), ...] (scanline fill)."""
    ys = [p[1] for p in points]
    for y in range(max(0, min(ys)), min(H, max(ys) + 1)):
        xs = []
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                t = (y - y0) / (y1 - y0)
                xs.append(x0 + t * (x1 - x0))
        if len(xs) >= 2:
            xs.sort()
            span(y, int(xs[0]), int(xs[-1]) + 1, color)


# ------------------------------------------------------------------- font

# A hand-drawn 5x7 bitmap font.  '#' is a set pixel.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "'": ("00100", "00100", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00000", "00100"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    ",": ("00000", "00000", "00000", "00000", "00000", "00100", "01000"),
}

GLYPH_W = 5
GLYPH_H = 7


def text_width(text, scale, tracking=None):
    if tracking is None:
        tracking = scale
    return len(text) * GLYPH_W * scale + max(0, len(text) - 1) * tracking


def draw_text(text, x, y, scale, color, shadow=None, shadow_dx=0, shadow_dy=0):
    """Draw text with its top-left corner at (x, y)."""
    tracking = scale
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(GLYPH_H):
            bits = glyph[row]
            for col in range(GLYPH_W):
                if bits[col] == "1":
                    px = cx + col * scale
                    py = y + row * scale
                    if shadow is not None:
                        rect(px + shadow_dx, py + shadow_dy, scale, scale, shadow)
                    rect(px, py, scale, scale, color)
        cx += GLYPH_W * scale + tracking


def draw_text_centered(text, y, scale, color, shadow=None, shadow_dx=0, shadow_dy=0):
    x = (W - text_width(text, scale)) // 2
    draw_text(text, x, y, scale, color, shadow, shadow_dx, shadow_dy)


# ------------------------------------------------------------------ scene

IVORY = rgb(250, 240, 214)
SHADOW = rgb(28, 22, 58)
CREAM = rgb(244, 228, 188)
GOLD = rgb(255, 206, 110)
PALE_SUN = rgb(255, 232, 168)
WATER = rgb(214, 236, 232)
ISLE_DARK = rgb(16, 48, 62)
ISLE_MID = rgb(24, 74, 78)
TERRACE_A = rgb(52, 116, 88)
TERRACE_B = rgb(74, 142, 100)
TERRACE_C = rgb(96, 164, 108)


def sky():
    stops = [
        (0.00, (34, 28, 82)),
        (0.30, (86, 52, 116)),
        (0.55, (178, 84, 112)),
        (0.75, (232, 138, 96)),
        (1.00, (252, 186, 96)),
    ]
    for y in range(0, 648):
        t = y / 647
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                f = 0 if t1 == t0 else (t - t0) / (t1 - t0)
                span(y, 0, W, rgb(*lerp(c0, c1, f)))
                break


def stars():
    # A few early stars in the deep part of the sky (fixed seed, no random).
    seed = 1234567

    def rnd():
        nonlocal seed
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        return seed

    for _ in range(90):
        x = rnd() % W
        y = rnd() % 190
        s = 1 + (rnd() % 2)
        c = (235, 228, 255) if rnd() % 3 else (255, 240, 200)
        rect(x, y, s, s, rgb(*c))


def sun():
    # Glow rings, then the disc itself.
    disc(512, 452, 168, rgb(248, 164, 96))
    disc(512, 452, 138, rgb(252, 186, 106))
    disc(512, 452, 112, rgb(255, 212, 128))
    disc(512, 452, 88, PALE_SUN)


def clouds():
    # Soft flat clouds, pale rose against the dusk.
    rose = rgb(246, 178, 158)
    pale = rgb(250, 204, 172)
    for cx, cy, rx, ry, col in [
        (180, 300, 120, 16, rose),
        (230, 288, 80, 12, pale),
        (840, 250, 130, 15, rose),
        (890, 238, 76, 11, pale),
        (700, 540, 90, 11, pale),
        (120, 560, 70, 9, rose),
    ]:
        ellipse(cx, cy, rx, ry, col)


def mountains():
    # A far ridge in silhouette along the horizon.
    ridge = [
        (0, 648), (0, 606), (90, 578), (170, 612), (250, 572), (330, 606),
        (420, 584), (512, 616), (600, 580), (690, 610), (780, 576),
        (870, 608), (950, 590), (1024, 612), (1024, 648),
    ]
    poly_rows(ridge, rgb(58, 44, 96))


def sea():
    stops = [
        (0.00, (214, 150, 96)),
        (0.18, (120, 96, 96)),
        (0.45, (28, 82, 100)),
        (1.00, (12, 48, 72)),
    ]
    for y in range(648, H):
        t = (y - 648) / (H - 648)
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                f = 0 if t1 == t0 else (t - t0) / (t1 - t0)
                span(y, 0, W, rgb(*lerp(c0, c1, f)))
                break
    # Sunlight on the water: a glittering column under the sun.
    for i, y in enumerate(range(656, 1000, 14)):
        fade = 1 - (y - 656) / 360
        w = int(150 * fade) + 26
        col = lerp((255, 214, 140), (40, 90, 104), 1 - fade)
        span(y, 512 - w // 2, 512 + w // 2, rgb(*col))
        span(y + 6, 512 - w // 3, 512 + w // 3, rgb(*lerp(col, (255, 230, 170), 0.5)))


def island(cx, top, w, h, scale=1.0):
    """A floating terraced isle: a flat top, stepped terraces, and a
    rocky underside tapering to a point, with waterfalls pouring down."""
    # Rocky underside: a wide top narrowing to a point.
    tip_y = top + h
    mid_y = top + int(h * 0.45)
    poly_rows(
        [
            (cx - w // 2, top + 6),
            (cx + w // 2, top + 6),
            (cx + int(w * 0.30), mid_y),
            (cx + int(w * 0.10), tip_y - 14),
            (cx, tip_y),
            (cx - int(w * 0.10), tip_y - 14),
            (cx - int(w * 0.30), mid_y),
        ],
        ISLE_DARK,
    )
    # Terraced top: stacked bands of green-gold.
    bands = [
        (top, int(w * 0.50), TERRACE_C),
        (top + 12, int(w * 0.44), TERRACE_B),
        (top + 24, int(w * 0.38), TERRACE_A),
    ]
    for by, bw, col in bands:
        bw = int(bw * scale)
        poly_rows(
            [(cx - bw, by), (cx + bw, by),
             (cx + int(bw * 0.92), by + 12), (cx - int(bw * 0.92), by + 12)],
            col,
        )
    # Lit rim along the top edge where the sun catches it.
    span(top, cx - int(w * 0.50 * scale), cx + int(w * 0.50 * scale), GOLD)
    # A few warm windows on the rock face.
    for wx, wy in [(-0.28, 0.52), (0.05, 0.58), (0.30, 0.50), (-0.08, 0.68)]:
        rect(int(cx + wx * w), int(top + wy * h), 5, 7, rgb(255, 214, 130))
    # Waterfalls spilling from the isle's rim down toward the sea.
    for fx, fw in [(-0.32, 7), (-0.05, 9), (0.24, 6)]:
        fx = int(cx + fx * w)
        for y in range(top + 40, 648, 3):
            span(y, fx, fx + fw, WATER if (y // 6) % 2 == 0 else rgb(190, 224, 220))
    # Mist where the falls meet the sea.
    ellipse(cx, 654, int(w * 0.22), 8, rgb(200, 224, 218))


def birds():
    for cx, cy, s in [(300, 330, 12), (340, 306, 9), (700, 300, 11), (742, 332, 8), (640, 268, 7)]:
        span(cy, cx - s, cx, rgb(40, 30, 66))
        span(cy, cx, cx + s, rgb(40, 30, 66))
        span(cy + 2, cx - s + 2, cx - 1, rgb(40, 30, 66))
        span(cy + 2, cx + 1, cx + s - 2, rgb(40, 30, 66))


def frame():
    rect(0, 0, W, 14, CREAM)
    rect(0, H - 14, W, 14, CREAM)
    rect(0, 0, 14, H, CREAM)
    rect(W - 14, 0, 14, H, CREAM)
    rect(26, 26, W - 52, 3, rgb(250, 240, 214))
    rect(26, H - 29, W - 52, 3, rgb(250, 240, 214))
    rect(26, 26, 3, H - 52, rgb(250, 240, 214))
    rect(W - 29, 26, 3, H - 52, rgb(250, 240, 214))


def paint():
    sky()
    stars()
    sun()
    clouds()
    mountains()
    sea()
    # The three isles: one great landmark, two smaller companions.
    island(512, 428, 430, 150)
    island(238, 372, 210, 96, 0.8)
    island(796, 344, 180, 84, 0.75)
    birds()
    frame()
    # Type: the place name leads, then the promise, then the invitation.
    draw_text_centered("VELMARA", 64, 15, IVORY, SHADOW, 5, 6)
    draw_text_centered("ISLES ABOVE THE GOLDEN SEA", 216, 4, IVORY, SHADOW, 2, 2)
    draw_text_centered("SAIL BEYOND THE LAST MAP", 956, 3, IVORY, SHADOW, 2, 2)


# -------------------------------------------------------------------- png

def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += canvas[y * W * 3:(y + 1) * W * 3]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    paint()
    size = write_png(OUT)
    print(f"wrote {OUT}: {W}x{H}, {size} bytes")


if __name__ == "__main__":
    main()
