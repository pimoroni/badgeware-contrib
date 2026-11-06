# Effects drawn over any theme's scene to show how many agents are working (the activity
# tier, see scene.tier_for). Each tier adds a little more, so all 15 look different:
#   1-10    one agent at a time: more and faster speed lines (the gait comes from the theme)
#   11-14   the bands 11-25, 26-50, 51-75, 76-100: sparks, then heat haze, then a pulsing edge
#   15      ULTRA, over 100 agents: the scene dims behind hyperspace star streaks
# Only the scene area is touched, never the theme's top bar or caption. Nothing is
# allocated per frame.

import math

# per tier: speed lines, sparks, haze alpha, pulsing edge
LINES = (0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 13, 15, 17, 0)
SPARKS = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 8, 12, 16, 0)
HAZE = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 26, 38, 0)
EDGE = (False,) * 14 + (True, False)

STREAKS = 40
_DIRS = [(math.cos(i * 2.39996), math.sin(i * 2.39996)) for i in range(STREAKS)]   # golden-angle spread


def draw(tier, t, top, bottom):
    if tier <= 0:
        return
    tier = min(tier, 15)
    if tier == 15:
        hyperspace(t, top, bottom)
        return
    h = bottom - top
    if HAZE[tier]:
        screen.pen = color.rgb(255, 140, 40, HAZE[tier])
        screen.rectangle(0, top, 160, h)
    if EDGE[tier]:
        a = int(70 + 60 * math.sin(t / 160.0))
        screen.pen = color.rgb(255, 70, 40, a)
        screen.rectangle(0, top, 3, h)
        screen.rectangle(157, top, 3, h)
    speed = 0.12 + 0.02 * tier            # pixels per millisecond
    screen.pen = color.rgb(255, 255, 255, 210)
    for i in range(LINES[tier]):
        y = top + 3 + (i * 37 + 11) % (h - 6)
        length = 6 + (i * 13) % 15
        x = 160 - int((t * speed + i * 53) % 200)
        screen.rectangle(x, y, length, 1)
    n = SPARKS[tier]
    if n:
        k = t // 70
        for i in range(n):
            seed = (i * 7919 + k * 104729) % 65521
            x = seed % 160
            y = top + (seed // 160) % h
            screen.pen = color.rgb(255, 230 - (seed % 3) * 40, 120, 220)
            screen.rectangle(x, y, 2 if seed % 5 == 0 else 1, 1)


def hyperspace(t, top, bottom):
    """Over 100 agents: the scene dims and stars streak out from a vanishing point."""
    h = bottom - top
    screen.pen = color.rgb(6, 8, 30, 150)
    screen.rectangle(0, top, 160, h)
    cx, cy = 80, top + h // 2
    for i in range(STREAKS):
        dx, dy = _DIRS[i]
        phase = ((t / 900.0) + i / STREAKS) % 1.0
        r0 = 3 + phase * phase * 110
        r1 = r0 + 4 + phase * 22
        x0, y0 = cx + dx * r0, cy + dy * r0
        x1, y1 = cx + dx * r1, cy + dy * r1
        # keep the streaks inside the scene area
        if y0 < top or y0 >= bottom:
            continue
        if y1 < top:
            x1, y1 = x0 + (x1 - x0) * (top - y0) / (y1 - y0), top
        elif y1 >= bottom:
            x1, y1 = x0 + (x1 - x0) * (bottom - 1 - y0) / (y1 - y0), bottom - 1
        b = int(120 + 135 * phase)
        screen.pen = color.rgb(b * 3 // 4, b * 7 // 8, b, 255)
        screen.line(int(x0), int(y0), int(x1), int(y1))
