# Drawing helpers shared by all themes. Runs on the badge and in the simulator.
#
# `image`, `color`, `rect`, `vec2` and `screen` are badge globals (picovector);
# the simulator installs compatible stand-ins.

W = 160
H = 120


def rgb(c):
    return color.rgb(c[0], c[1], c[2])


def palette(slots):
    """slots: dict slot-index -> (r, g, b). Returns a list usable by to_image."""
    out = [None] * 16
    for k in slots:
        out[k] = rgb(slots[k])
    return out


def to_image(grid, pal):
    """Turn a palette-indexed figure.Grid into an image (run-length rectangles)."""
    img = image(grid.w, grid.h)
    w = grid.w
    px = grid.px
    for y in range(grid.h):
        row = y * w
        x = 0
        while x < w:
            c = px[row + x]
            if not c:
                x += 1
                continue
            x0 = x
            while x < w and px[row + x] == c:
                x += 1
            p = pal[c]
            if p is not None:
                img.pen = p
                img.rectangle(x0, y, x - x0, 1)
    return img


def sprite(rows, keys):
    """Hand-drawn sprite from ASCII rows. keys maps char -> (r, g, b)."""
    h = len(rows)
    w = max(len(r) for r in rows)
    img = image(w, h)
    pens = {}
    for ch in keys:
        pens[ch] = rgb(keys[ch])
    for y, row in enumerate(rows):
        x = 0
        n = len(row)
        while x < n:
            ch = row[x]
            if ch not in pens:
                x += 1
                continue
            x0 = x
            while x < n and row[x] == ch:
                x += 1
            img.pen = pens[ch]
            img.rectangle(x0, y, x - x0, 1)
    return img


def blit(img, x, y, scale=1, flip=False):
    w = img.width * scale
    screen.blit(img, rect(int(x), int(y), -w if flip else w, img.height * scale))


def box(x, y, w, h, c):
    screen.pen = c if not isinstance(c, tuple) else rgb(c)
    screen.rectangle(int(x), int(y), int(w), int(h))


def text(s, x, y, c, fnt=None, shadow=None):
    if fnt is not None:
        screen.font = fnt
    if shadow is not None:
        screen.pen = shadow if not isinstance(shadow, tuple) else rgb(shadow)
        screen.text(s, int(x) + 1, int(y) + 1)
    screen.pen = c if not isinstance(c, tuple) else rgb(c)
    screen.text(s, int(x), int(y))


def width(s, fnt=None):
    if fnt is not None:
        screen.font = fnt
    return screen.measure_text(s)[0]


def ctext(s, cx, y, c, fnt=None, shadow=None):
    w = width(s, fnt)
    text(s, cx - w / 2, y, c, None, shadow)


def fit(s, max_w, fnt):
    """Trim text with '..' so it fits max_w pixels."""
    screen.font = fnt
    if screen.measure_text(s)[0] <= max_w:
        return s
    while s and screen.measure_text(s + "..")[0] > max_w:
        s = s[:-1]
    return s + ".."


def wrap(s, max_w, fnt):
    """Greedy word wrap to max_w pixels."""
    screen.font = fnt
    lines = []
    cur = ""
    for word in s.split(" "):
        test = word if not cur else cur + " " + word
        if screen.measure_text(test)[0] <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def countdown(us):
    """Time left until a usage window resets, from microseconds (int).

    Hours and minutes while it is far off, a ticking clock under an hour,
    milliseconds in the last minute and microseconds in the last ten seconds.
    """
    if us is None:
        return "--:--"
    if us <= 0:
        # the window has rolled over: usage is back to full
        return "RESET!" if us > -60 * 1000000 else "FULL"
    s = us // 1000000
    if s >= 86400:
        return "%dD%02dH" % (s // 86400, s % 86400 // 3600)
    if s >= 3600:
        return "%dH%02dM" % (s // 3600, s % 3600 // 60)
    if s >= 60:
        return "%d:%02d" % (s // 60, s % 60)
    if s >= 10:
        return "%d.%03d" % (s, us % 1000000 // 1000)
    return "%d.%06d" % (s, us % 1000000)


def countdown_color(us, normal, soon=(255, 214, 90), now=(255, 90, 80)):
    if us is None or us > 600 * 1000000 or us <= -60 * 1000000:
        return normal
    return soon if us > 60 * 1000000 else now


CLOCK_ICON = (".KKK.", "KWWWK", "KWKWK", "KWWKK", ".KKK.")


def clock_icon(ink, face):
    return sprite(CLOCK_ICON, {"K": ink, "W": face})


# --------------------------------------------------------------- hearts

HEART = (
    ".KKK.KKK.",
    "KFWFKFFFK",
    "KFFFFFFFK",
    "KFFFFFFFK",
    ".KFFFFFK.",
    "..KFFFK..",
    "...KFK...",
    "....K....",
)


def heart_set(full, empty, outline, shine=(255, 255, 255)):
    """Three heart images: full, half, empty."""
    def make(left, right, gloss):
        rows = []
        for r in HEART:
            row = ""
            for i, ch in enumerate(r):
                if ch == "F":
                    row += "L" if i <= 4 else "R"
                elif ch == "W":
                    row += "W" if gloss else ("L" if i <= 4 else "R")
                else:
                    row += ch
            rows.append(row)
        return sprite(rows, {"K": outline, "L": left, "R": right, "W": shine})
    return make(full, full, True), make(full, empty, True), make(empty, empty, False)


def draw_hearts(hset, units, x, y, n=10, spacing=8, blink=False, unknown=None):
    """units: remaining half-hearts (0..2n) or None when unknown."""
    full, half, empty = hset
    for i in range(n):
        if units is None:
            img = unknown if unknown is not None else empty
        else:
            left = units - i * 2
            img = full if left >= 2 else (half if left == 1 else empty)
            if blink and img is not empty:
                img = empty
        screen.blit(img, vec2(int(x + i * spacing), int(y)))


def meter(x, y, w, h, frac, fg, bg, edge=None):
    if edge is not None:
        box(x - 1, y - 1, w + 2, h + 2, edge)
    box(x, y, w, h, bg)
    if frac is not None:
        fw = int(w * max(0.0, min(1.0, frac)) + 0.5)
        if fw:
            box(x, y, fw, h, fg)


def zzz(x, y, t, c, fnt):
    """Floating Z's for sleeping characters."""
    screen.font = fnt
    for i in range(3):
        p = ((t / 1400.0) + i / 3.0) % 1.0
        zx = x + p * 10 + i * 2
        zy = y - p * 18
        screen.pen = color.rgb(c[0], c[1], c[2], int(255 * (1 - p)))
        screen.text("z" if i < 2 else "Z", int(zx), int(zy))


def bubble(x, y, s, fg, bg, fnt):
    """Speech bubble anchored at its tail (x, y)."""
    w = int(width(s, fnt)) + 6
    h = int(screen.measure_text(s)[1]) + 2
    bx = int(max(1, min(W - w - 1, x - w // 2)))
    by = int(y - h - 4)
    box(bx - 1, by, w + 2, h, fg)
    box(bx, by - 1, w, h + 2, fg)
    box(bx, by, w, h, bg)
    box(x - 1, by + h, 3, 2, bg)
    box(x - 1, by + h + 2, 1, 2, fg)
    text(s, bx + 3, by + 1, fg)


def scanlines(y0, y1, alpha=40):
    screen.pen = color.rgb(0, 0, 0, alpha)
    for y in range(y0, y1, 2):
        screen.rectangle(0, y, W, 1)
