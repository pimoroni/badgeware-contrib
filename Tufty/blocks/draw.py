"""
Rendering for Tetris and Dr. Mario.

Tetris uses theme colours. Dr. Mario uses fixed colours (red/blue/yellow)
regardless of theme, because the gameplay depends on colour recognition.
"""

import math
from game import (PIECES, COLS, ROWS, HIDDEN, TOTAL,
                  DR_COLS, DR_ROWS, DR_HIDDEN, DR_TOTAL)


# ── Layout ───────────────────────────────────────────────────────────────────

SW = screen.width
SH = screen.height
CELL = 11

# Tetris board: centred
T_BW = COLS * CELL
T_BH = ROWS * CELL
T_BX = (SW - T_BW) // 2
T_BY = (SH - T_BH) // 2

# Dr. Mario board: centred
D_BW = DR_COLS * CELL
D_BH = DR_ROWS * CELL
D_BX = (SW - D_BW) // 2
D_BY = (SH - D_BH) // 2

CX = SW // 2
CY = SH // 2

small_font = pixel_font.load("/system/assets/fonts/winds.ppf")
large_font = pixel_font.load("/system/assets/fonts/ignore.ppf")

# Dr. Mario fixed colours: red, blue, yellow — always the same
DR_COLORS = [
    color.rgb(220, 30, 30),    # 0 = red
    color.rgb(30, 30, 220),    # 1 = blue
    color.rgb(220, 200, 30),   # 2 = yellow
]
DR_COLORS_HI = [
    color.rgb(255, 100, 100),
    color.rgb(100, 100, 255),
    color.rgb(255, 240, 100),
]
DR_BG = color.rgb(0, 0, 0)
DR_BOARD_BG = color.rgb(8, 8, 20)
DR_GRID = color.rgb(20, 20, 40)
DR_BORDER = color.rgb(50, 50, 90)
DR_PANEL_BG = color.rgb(14, 14, 30)
DR_LABEL = color.rgb(100, 110, 150)
DR_VALUE = color.rgb(255, 255, 255)


# ── Panel geometry ───────────────────────────────────────────────────────────

def _panels(bx, bw):
    lw = bx - 6
    lx = 3
    rx = bx + bw + 6
    rw = SW - rx - 3
    return lx, lw, rx, rw


# ── Text helpers ─────────────────────────────────────────────────────────────

def _cx(t):
    w, _ = screen.measure_text(t)
    return CX - w // 2


def _cxin(t, x, w):
    tw, _ = screen.measure_text(t)
    return x + (w - tw) // 2


def stc(t, y, big, th):
    """Shadow text, centred on screen."""
    screen.font = large_font if big else small_font
    x = _cx(t)
    screen.pen = th["ts"]
    screen.text(t, x + 1, y + 1)
    screen.pen = th["val"]
    screen.text(t, x, y)


def _stc_fixed(t, y, big, shadow, fg):
    """Shadow text centred with explicit colours."""
    screen.font = large_font if big else small_font
    x = _cx(t)
    screen.pen = shadow
    screen.text(t, x + 1, y + 1)
    screen.pen = fg
    screen.text(t, x, y)


def _lbl(t, x, w, y, c):
    screen.font = small_font
    screen.pen = c
    screen.text(t, _cxin(t, x, w), y)


def _val(t, x, w, y, c):
    screen.font = small_font
    screen.pen = c
    screen.text(t, _cxin(t, x, w), y)


# ── Block drawing ────────────────────────────────────────────────────────────

def draw_block(x, y, pt, th, sz=CELL):
    """Draw a themed Tetris block."""
    pc = th["pc"].get(pt)
    if pc is None:
        screen.pen = color.rgb(80, 80, 80)
        screen.shape(shape.rectangle(x, y, sz, sz))
        screen.pen = color.rgb(100, 100, 100)
        screen.shape(shape.rectangle(x + 1, y + 1, sz - 2, sz - 2))
        return
    m, h, s = pc
    screen.pen = s
    screen.shape(shape.rectangle(x, y, sz, sz))
    screen.pen = m
    screen.shape(shape.rectangle(x + 1, y + 1, sz - 2, sz - 2))
    screen.pen = h
    screen.shape(shape.rectangle(x + 1, y + 1, sz - 3, 1))
    screen.shape(shape.rectangle(x + 1, y + 1, 1, sz - 3))


def draw_virus(x, y, ci, sz=CELL):
    """Draw a Dr. Mario virus with eyes. ci = colour index 0-2."""
    screen.pen = DR_COLORS[ci]
    screen.shape(shape.rectangle(x, y, sz, sz))
    screen.pen = DR_COLORS_HI[ci]
    screen.shape(shape.rectangle(x + 1, y + 1, sz - 3, 1))
    # Eyes
    screen.pen = color.rgb(255, 255, 255)
    screen.shape(shape.rectangle(x + 2, y + 3, 2, 2))
    screen.shape(shape.rectangle(x + sz - 4, y + 3, 2, 2))
    screen.pen = color.rgb(0, 0, 0)
    screen.shape(shape.rectangle(x + 3, y + 4, 1, 1))
    screen.shape(shape.rectangle(x + sz - 3, y + 4, 1, 1))


def draw_pill_cell(x, y, ci, sz=CELL):
    """Draw a Dr. Mario pill half. ci = colour index 0-2."""
    screen.pen = DR_COLORS[ci]
    screen.shape(shape.rounded_rectangle(x, y, sz, sz, 3))
    screen.pen = DR_COLORS_HI[ci]
    screen.shape(shape.rectangle(x + 2, y + 2, sz - 5, 1))


def draw_mini(pt, cx, cy, th, cs=7):
    """Draw a small Tetris piece preview."""
    if pt is None:
        return
    cells = PIECES[pt][0]
    mnr = min(r for r, c in cells)
    mxr = max(r for r, c in cells)
    mnc = min(c for r, c in cells)
    mxc = max(c for r, c in cells)
    ox = cx - ((mxc - mnc + 1) * cs) // 2
    oy = cy - ((mxr - mnr + 1) * cs) // 2
    for dr, dc in cells:
        draw_block(ox + (dc - mnc) * cs, oy + (dr - mnr) * cs, pt, th, cs)


def pbox(x, y, w, h, c):
    """Draw a panel background."""
    screen.pen = c
    screen.shape(shape.rounded_rectangle(x, y, w, h, 3))


# ── Backgrounds ──────────────────────────────────────────────────────────────

def draw_bg(tn, _th):
    """Draw a subtle animated background based on theme name."""
    t = badge.ticks / 1000
    if tn == "neon":
        screen.pen = color.rgb(40, 0, 60, 22)
        for i in range(0, SH, 16):
            screen.shape(shape.rectangle(0, (i + int(t * 30)) % SH, SW, 1))
    elif tn == "gameboy":
        screen.pen = color.rgb(30, 70, 30, 30)
        for y in range(0, SH, 8):
            for x in range(0, SW, 8):
                screen.shape(shape.rectangle(x + 3, y + 3, 2, 2))
    elif tn == "hacker":
        screen.pen = color.rgb(0, 70, 0, 30)
        for col in range(0, SW, 14):
            dy = int((t * 40 + col * 7) % (SH + 40)) - 20
            for j in range(3):
                y = dy - j * 10
                if 0 <= y < SH:
                    screen.shape(shape.rectangle(col, y, 8, 8))
    elif tn == "vaporwave":
        for i in range(0, SH, 14):
            p = math.sin(t * 0.5 + i * 0.02) * 0.5 + 0.5
            screen.pen = color.rgb(int(35 + p * 18), 0, int(45 + (1 - p) * 18), 15)
            screen.shape(shape.rectangle(0, i, SW, 10))
    elif tn == "forest":
        screen.pen = color.rgb(25, 45, 18, 22)
        for i in range(0, SW, 24):
            screen.shape(shape.rectangle(i + 8, 0, 3, SH))
    elif tn == "lava":
        for i in range(4):
            x = int((math.sin(t * 0.4 + i * 2) * 0.5 + 0.5) * SW)
            y = SH - int((t * 15 + i * 40) % (SH + 20))
            screen.pen = color.rgb(70, 18, 0, 18)
            screen.shape(shape.rounded_rectangle(x - 8, y - 6, 16, 12, 4))
    elif tn == "ice":
        screen.pen = color.rgb(25, 45, 70, 16)
        for i in range(-SH, SW, 30):
            screen.shape(shape.line(i, 0, i + SH // 2, SH, 1))
    elif tn == "monochrome":
        screen.pen = color.rgb(18, 18, 18, 25)
        for i in range(-SH, SW, 24):
            screen.shape(shape.line(i, 0, i + SH, SH, 1))
    elif tn == "pastel":
        for i in range(3):
            bx = int((math.sin(t * 0.3 + i * 1.5) * 0.5 + 0.5) * SW)
            by = int((math.cos(t * 0.2 + i * 1.1) * 0.5 + 0.5) * SH)
            screen.pen = color.rgb(210, 170, 190, 10)
            screen.shape(shape.rounded_rectangle(bx - 15, by - 15, 30, 30, 10))
    else:
        screen.pen = color.rgb(18, 18, 30, 16)
        for i in range(5):
            x = (i * 43 + 10) % SW
            y = int((t * 12 + i * 30) % (SH + 20)) - 10
            screen.shape(shape.rectangle(x, y, 10, 10))


# ── Tetris rendering ────────────────────────────────────────────────────────

def draw_tetris_board(g, th):
    bx, by = T_BX, T_BY
    screen.pen = th["bbg"]
    screen.shape(shape.rectangle(bx, by, T_BW, T_BH))
    if g.danger:
        screen.pen = th["dng"]
        screen.shape(shape.rectangle(bx, by, T_BW, CELL * 4))
    screen.pen = th["grd"]
    for c in range(1, COLS):
        screen.shape(shape.line(bx + c * CELL, by, bx + c * CELL, by + T_BH, 1))
    for r in range(1, ROWS):
        screen.shape(shape.line(bx, by + r * CELL, bx + T_BW, by + r * CELL, 1))
    gr = g.topout_anim.gray_row() if g.topout_anim else -1
    for r in range(HIDDEN, TOTAL):
        vr = r - HIDDEN
        for c in range(COLS):
            cell = g.board[r][c]
            if cell is not None:
                x, y = bx + c * CELL, by + vr * CELL
                if vr <= gr:
                    screen.pen = color.rgb(40, 40, 40)
                    screen.shape(shape.rectangle(x, y, CELL, CELL))
                else:
                    draw_block(x, y, cell, th)
    # Border
    screen.pen = th["pbr"]
    for edge in [(bx - 1, by - 1, T_BW + 2, 1), (bx - 1, by + T_BH, T_BW + 2, 1),
                 (bx - 1, by - 1, 1, T_BH + 2), (bx + T_BW, by - 1, 1, T_BH + 2)]:
        screen.shape(shape.rectangle(*edge))


def draw_tetris_piece(g, th):
    if g.piece is None:
        return
    bx, by = T_BX, T_BY
    gy = g.ghost_y()
    screen.pen = th["gho"]
    for dr, dc in g.cells(g.piece, g.piece_rot):
        r, c = gy + dr - HIDDEN, g.piece_x + dc
        if r >= 0:
            screen.shape(shape.rectangle(bx + c * CELL + 1, by + r * CELL + 1, CELL - 2, CELL - 2))
    for dr, dc in g.cells(g.piece, g.piece_rot):
        r, c = g.piece_y + dr - HIDDEN, g.piece_x + dc
        if r >= 0:
            draw_block(bx + c * CELL, by + r * CELL, g.piece, th)


def draw_tetris_line_anim(g, th):
    if g.line_anim is None:
        return
    p = g.line_anim.progress()
    for r in g.line_anim.rows:
        y = T_BY + (r - HIDDEN) * CELL
        if p < 0.5:
            screen.pen = color.rgb(255, 255, 255, int(255 * (1 - p * 2)))
        else:
            screen.pen = th["bbg"]
        screen.shape(shape.rectangle(T_BX, y, T_BW, CELL))


def draw_tetris_panels(g, th):
    lx, lw, rx, rw = _panels(T_BX, T_BW)
    # Hold
    pbox(lx, T_BY, lw, 50, th["pbg"])
    _lbl("HOLD", lx, lw, T_BY + 4, th["lbl"])
    if g.hold_piece:
        draw_mini(g.hold_piece, lx + lw // 2, T_BY + 33, th)
    # Score
    sy = T_BY + 56
    pbox(lx, sy, lw, 68, th["pbg"])
    _lbl("SCORE", lx, lw, sy + 4, th["lbl"])
    _val(str(g.score), lx, lw, sy + 18, th["val"])
    _lbl("BEST", lx, lw, sy + 36, th["lbl"])
    _val(str(g.stats.high_score), lx, lw, sy + 50, th["val"])
    # Next
    pbox(rx, T_BY, rw, 86, th["pbg"])
    _lbl("NEXT", rx, rw, T_BY + 4, th["lbl"])
    for i, pn in enumerate(g.next_queue):
        draw_mini(pn, rx + rw // 2, T_BY + 22 + i * 22, th)
    # Level / Lines
    ly = T_BY + 92
    pbox(rx, ly, rw, 52, th["pbg"])
    _lbl("LEVEL", rx, rw, ly + 4, th["lbl"])
    _val(str(g.level), rx, rw, ly + 16, th["val"])
    _lbl("LINES", rx, rw, ly + 30, th["lbl"])
    _val(str(g.lines), rx, rw, ly + 42, th["val"])
    # Speed bar
    pbox(rx, ly + 58, rw, 12, th["pbg"])
    bw = max(1, rw - 8)
    spd = g.current_speed()
    fill = max(2, min(int((1 - max(0, spd - 33) / 767) * bw), bw))
    screen.pen = th["pbr"]
    screen.shape(shape.rectangle(rx + 4, ly + 62, bw, 4))
    screen.pen = color.rgb(int(255 * fill / max(1, bw)), int(255 * (1 - fill / max(1, bw))), 60)
    screen.shape(shape.rectangle(rx + 4, ly + 62, fill, 4))


# ── Dr. Mario rendering ─────────────────────────────────────────────────────

def draw_dr_board(g):
    bx, by = D_BX, D_BY
    screen.pen = DR_BOARD_BG
    screen.shape(shape.rectangle(bx, by, D_BW, D_BH))
    screen.pen = DR_GRID
    for c in range(1, DR_COLS):
        screen.shape(shape.line(bx + c * CELL, by, bx + c * CELL, by + D_BH, 1))
    for r in range(1, DR_ROWS):
        screen.shape(shape.line(bx, by + r * CELL, bx + D_BW, by + r * CELL, 1))
    for r in range(DR_HIDDEN, DR_TOTAL):
        vr = r - DR_HIDDEN
        for c in range(DR_COLS):
            cell = g.board[r][c]
            if cell is not None:
                x, y = bx + c * CELL, by + vr * CELL
                if cell >= 10:
                    draw_virus(x, y, cell % 10)
                else:
                    draw_pill_cell(x, y, cell)
    # Border
    screen.pen = DR_BORDER
    for edge in [(bx - 1, by - 1, D_BW + 2, 1), (bx - 1, by + D_BH, D_BW + 2, 1),
                 (bx - 1, by - 1, 1, D_BH + 2), (bx + D_BW, by - 1, 1, D_BH + 2)]:
        screen.shape(shape.rectangle(*edge))


def draw_dr_pill(g):
    bx, by = D_BX, D_BY
    cells = g.pill_cells(g.pill_x, g.pill_y, g.pill_rot)
    colors = [g.pill_a, g.pill_b]
    for i, (r, c) in enumerate(cells):
        vr = r - DR_HIDDEN
        if vr >= 0:
            draw_pill_cell(bx + c * CELL, by + vr * CELL, colors[i])


def draw_dr_line_anim(g):
    if g.line_anim is None:
        return
    p = g.line_anim.progress()
    for r in g.line_anim.rows:
        vr = r - DR_HIDDEN
        if 0 <= vr < DR_ROWS:
            y = D_BY + vr * CELL
            if p < 0.5:
                screen.pen = color.rgb(255, 255, 255, int(255 * (1 - p * 2)))
            else:
                screen.pen = DR_BOARD_BG
            screen.shape(shape.rectangle(D_BX, y, D_BW, CELL))


def draw_dr_panels(g):
    lx, lw, rx, rw = _panels(D_BX, D_BW)
    # Next pill
    pbox(lx, D_BY, lw, 40, DR_PANEL_BG)
    _lbl("NEXT", lx, lw, D_BY + 4, DR_LABEL)
    cx = lx + lw // 2
    draw_pill_cell(cx - CELL, D_BY + 22, g.next_a, CELL)
    draw_pill_cell(cx, D_BY + 22, g.next_b, CELL)
    # Score
    sy = D_BY + 46
    pbox(lx, sy, lw, 50, DR_PANEL_BG)
    _lbl("SCORE", lx, lw, sy + 4, DR_LABEL)
    _val(str(g.score), lx, lw, sy + 18, DR_VALUE)
    _lbl("BEST", lx, lw, sy + 32, DR_LABEL)
    _val(str(g.stats.dr_high), lx, lw, sy + 44, DR_VALUE)
    # Level
    pbox(rx, D_BY, rw, 40, DR_PANEL_BG)
    _lbl("LEVEL", rx, rw, D_BY + 4, DR_LABEL)
    _val(str(g.level), rx, rw, D_BY + 20, DR_VALUE)
    # Viruses
    pbox(rx, D_BY + 46, rw, 40, DR_PANEL_BG)
    _lbl("VIRUSES", rx, rw, D_BY + 50, DR_LABEL)
    _val(str(g.viruses), rx, rw, D_BY + 66, DR_VALUE)


# ── Shared screens ───────────────────────────────────────────────────────────

def draw_popup(g, bx, by, bw, bh):
    """Draw score popup text over the board."""
    if not g.popup_active():
        return
    txt, start = g.popup
    el = badge.ticks - start
    alpha = max(0, 255 - int(el * 255 / 800))
    screen.font = large_font
    screen.pen = color.rgb(255, 255, 100, alpha)
    w, _ = screen.measure_text(txt)
    screen.text(txt, bx + bw // 2 - w // 2, by + bh // 2 - 8)


def draw_title(th, tn, game_sel, stats):
    """Title screen with two game choices."""
    screen.pen = th["bg"]
    screen.clear()
    draw_bg(tn, th)

    t = badge.ticks / 1000
    for i in range(5):
        bx = int((math.sin(t * 0.5 + i * 1.3) * 0.5 + 0.5) * (SW - 50)) + 15
        by = int((math.cos(t * 0.3 + i * 0.9) * 0.5 + 0.5) * (SH - 50)) + 15
        screen.pen = th["grd"]
        screen.shape(shape.rectangle(bx, by, 12, 12))

    # Two game selection boxes
    bw = 110
    bh = 36
    gap = 16
    x1 = CX - bw - gap // 2
    x2 = CX + gap // 2
    by = 50

    for i, (x, name) in enumerate([(x1, "TETRIS"), (x2, "DR.MARIO")]):
        if i == game_sel:
            screen.pen = th["pbr"]
            screen.shape(shape.rounded_rectangle(x, by, bw, bh, 5))
            screen.pen = th["pbg"]
            screen.shape(shape.rounded_rectangle(x + 2, by + 2, bw - 4, bh - 4, 4))
            screen.pen = th["val"]
        else:
            screen.pen = th["pbg"]
            screen.shape(shape.rounded_rectangle(x, by, bw, bh, 5))
            screen.pen = th["lbl"]
        screen.font = large_font
        w, _ = screen.measure_text(name)
        screen.text(name, x + bw // 2 - w // 2, by + 6)

    screen.font = small_font
    screen.pen = th["lbl"]
    screen.text("< A          C >", _cx("< A          C >"), by + bh + 8)

    if int(badge.ticks / 600) % 2:
        stc("B to play", CY + 30, True, th)

    screen.font = small_font
    screen.pen = th["lbl"]
    hs = "Best: {} / Dr: {}".format(stats.high_score, stats.dr_high)
    screen.text(hs, _cx(hs), SH - 36)
    screen.pen = th["grd"]
    screen.text("A+B pause  A+C hold", _cx("A+B pause  A+C hold"), SH - 22)
    screen.text("UP:Rot DN:Soft B:Drop", _cx("UP:Rot DN:Soft B:Drop"), SH - 10)


PAUSE_ITEMS = ["Resume", "Theme", "Stats", "Quit"]


def draw_pause(th, sel):
    screen.pen = color.rgb(0, 0, 0, 170)
    screen.shape(shape.rectangle(0, 0, SW, SH))
    stc("PAUSED", CY - 50, True, th)
    screen.font = small_font
    for i, item in enumerate(PAUSE_ITEMS):
        y = CY - 15 + i * 22
        if i == sel:
            screen.pen = th["pbr"]
            screen.shape(shape.rounded_rectangle(CX - 50, y - 3, 100, 18, 3))
            screen.pen = th["val"]
        else:
            screen.pen = th["lbl"]
        screen.text(item, _cx(item), y)


def draw_themes(names, sel, th, tn):
    screen.pen = th["bg"]
    screen.clear()
    draw_bg(tn, th)
    stc("THEME", 20, True, th)
    screen.font = small_font
    vis = 8
    start = max(0, sel - vis // 2)
    if start + vis > len(names):
        start = max(0, len(names) - vis)
    for i in range(start, min(start + vis, len(names))):
        y = 52 + (i - start) * 20
        n = names[i]
        if i == sel:
            screen.pen = th["pbr"]
            screen.shape(shape.rounded_rectangle(CX - 55, y - 3, 110, 18, 3))
            screen.pen = th["val"]
        else:
            screen.pen = th["lbl"]
        screen.text(n, _cx(n), y)
    screen.pen = th["lbl"]
    screen.text("UP/DN B:OK A:Back", _cx("UP/DN B:OK A:Back"), SH - 10)


def draw_stats(stats, th, tn):
    screen.pen = th["bg"]
    screen.clear()
    draw_bg(tn, th)
    stc("STATS", 12, True, th)
    screen.font = small_font
    items = [
        ("Tetris Best", str(stats.high_score)),
        ("Dr.Mario Best", str(stats.dr_high)),
        ("Dr.Mario Level", str(stats.dr_best_level)),
        ("Games", str(stats.total_games)),
        ("Lines", str(stats.total_lines)),
        ("Best Combo", str(stats.best_combo)),
        ("Best B2B", str(stats.best_b2b)),
        ("Time", stats.play_time_str()),
    ]
    y = 38
    for lb, vl in items:
        screen.pen = th["lbl"]
        screen.text(lb, 16, y)
        screen.pen = th["val"]
        vw, _ = screen.measure_text(vl)
        screen.text(vl, SW - 16 - vw, y)
        y += 22
    screen.pen = th["lbl"]
    screen.text("A: Back", _cx("A: Back"), SH - 10)


def draw_gameover(g, stats, is_dr=False):
    screen.pen = color.rgb(0, 0, 0, 180)
    screen.shape(shape.rectangle(0, 0, SW, SH))
    _stc_fixed("GAME OVER", CY - 35, True, color.rgb(0, 0, 0, 200), color.rgb(255, 255, 255))
    screen.font = small_font
    screen.pen = color.rgb(180, 190, 210)
    st = "Score: {}".format(g.score)
    screen.text(st, _cx(st), CY + 5)
    best = stats.dr_high if is_dr else stats.high_score
    if g.score >= best and g.score > 0:
        screen.pen = color.rgb(255, 220, 50)
        screen.text("NEW BEST!", _cx("NEW BEST!"), CY + 22)
    if int(badge.ticks / 600) % 2:
        _stc_fixed("B:Again  A:Title", CY + 48, False,
                   color.rgb(0, 0, 0, 160), color.rgb(200, 200, 200))


def draw_level_clear(g):
    screen.pen = color.rgb(0, 0, 0, 140)
    screen.shape(shape.rectangle(0, 0, SW, SH))
    _stc_fixed("LEVEL CLEAR!", CY - 20, True,
               color.rgb(0, 0, 0, 200), color.rgb(255, 255, 100))
    screen.font = small_font
    screen.pen = color.rgb(200, 200, 200)
    lt = "Level {}".format(g.level)
    screen.text(lt, _cx(lt), CY + 15)
    if int(badge.ticks / 500) % 2:
        _stc_fixed("B to continue", CY + 40, False,
                   color.rgb(0, 0, 0, 140), color.rgb(180, 180, 180))
