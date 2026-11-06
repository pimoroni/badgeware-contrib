# Procedural pixel-art figures.
#
# A figure is a tiny skeleton (hip, torso, two legs, two arms, head) posed by a
# handful of joint angles. It is rasterised into a palette-indexed Grid, given a
# one-pixel outline, then turned into a picovector image by gfx.to_image().
# Everything here is plain Python so it runs on the badge (MicroPython) and in
# the desktop simulator (CPython) unchanged.
#
# Angles are in degrees. 0 points straight down the screen, positive angles
# swing toward +x, which is the direction every figure faces.

import math

_RAD = math.pi / 180


def _sc(a):
    a = a * _RAD
    return math.sin(a), math.cos(a)


class Grid:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h)

    def set(self, x, y, c):
        x = int(x + 0.5) if x >= 0 else int(x - 0.5)
        y = int(y + 0.5) if y >= 0 else int(y - 0.5)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y * self.w + x] = c

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y * self.w + x]
        return 0

    def rect(self, x, y, w, h, c):
        for yy in range(int(y), int(y + h)):
            for xx in range(int(x), int(x + w)):
                if 0 <= xx < self.w and 0 <= yy < self.h:
                    self.px[yy * self.w + xx] = c

    def disc(self, cx, cy, r, c):
        r2 = r * r + r * 0.8
        for yy in range(int(cy - r - 1), int(cy + r + 2)):
            for xx in range(int(cx - r - 1), int(cx + r + 2)):
                dx = xx - cx
                dy = yy - cy
                if dx * dx + dy * dy <= r2 and 0 <= xx < self.w and 0 <= yy < self.h:
                    self.px[yy * self.w + xx] = c

    def seg(self, x0, y0, x1, y1, thick, c):
        dx = x1 - x0
        dy = y1 - y0
        n = int(max(abs(dx), abs(dy)) * 2) + 1
        lo = -(thick // 2)
        hi = lo + thick
        for i in range(n + 1):
            t = i / n
            x = x0 + dx * t
            y = y0 + dy * t
            xi = int(x + 0.5) if x >= 0 else int(x - 0.5)
            yi = int(y + 0.5) if y >= 0 else int(y - 0.5)
            for oy in range(lo, hi):
                for ox in range(lo, hi):
                    xx = xi + ox
                    yy = yi + oy
                    if 0 <= xx < self.w and 0 <= yy < self.h:
                        self.px[yy * self.w + xx] = c

    def rows(self, x, y, rows, keys):
        # Stamp hand-drawn ASCII rows; keys maps characters to palette indices.
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                c = keys.get(ch)
                if c:
                    xx = x + i
                    yy = y + j
                    if 0 <= xx < self.w and 0 <= yy < self.h:
                        self.px[yy * self.w + xx] = c

    def outline(self, oc):
        w = self.w
        h = self.h
        src = bytes(self.px)
        for y in range(h):
            for x in range(w):
                if src[y * w + x]:
                    continue
                if ((x > 0 and src[y * w + x - 1]) or (x < w - 1 and src[y * w + x + 1])
                        or (y > 0 and src[(y - 1) * w + x]) or (y < h - 1 and src[(y + 1) * w + x])):
                    self.px[y * w + x] = oc


# Palette slots shared by every figure. Themes map these to real colours.
T = 0          # transparent
OUT = 1        # outline
SKIN = 2
SKIN_D = 3     # far-side skin
HAIR = 4
TOP = 5        # shirt / tunic / suit
TOP_D = 6
BOT = 7        # trousers / shorts
BOT_D = 8
SHOE = 9
EYE = 10
ACC1 = 11      # accessories (cap, sword, shield, prop colours)
ACC2 = 12
ACC3 = 13
ACC4 = 14
WHITE = 15


class Spec:
    """Body proportions and costume rules for one character."""

    def __init__(self, **kw):
        self.torso = 7
        self.thigh = 5
        self.shin = 5
        self.upper = 4
        self.fore = 4
        self.head_r = 3
        self.torso_w = 4
        self.leg_w = 2
        self.arm_w = 2
        self.shins = BOT           # BOT for trousers, SKIN for shorts
        self.forearms = SKIN       # SKIN for short sleeves, TOP for long
        self.uppers = TOP
        self.thighs = BOT
        self.foot = 2
        self.hair = "short"        # short | long | bald | none
        self.hat = None            # None | "cap" | "hood" | "helmet"
        self.beard = False
        self.skirt = False         # tunic skirt below the belt (Link)
        self.belt = None
        self.extra = None          # fn(grid, joints, pose) for props
        self.w = 28
        self.h = 30
        for k in kw:
            setattr(self, k, kw[k])


class Pose:
    def __init__(self, lean=0, hip=(0, 0), lf=(0, 0), lb=(0, 0), af=(10, 20), ab=(-10, 20),
                 eye=True, mouth=False, prop=None):
        self.lean = lean
        self.hip = hip
        self.lf = lf
        self.lb = lb
        self.af = af
        self.ab = ab
        self.eye = eye
        self.mouth = mouth
        self.prop = prop


def _dark(c):
    return {SKIN: SKIN_D, TOP: TOP_D, BOT: BOT_D}.get(c, c)


def render(spec, pose, hip_xy=None):
    g = Grid(spec.w, spec.h)
    if hip_xy is None:
        hip_xy = (spec.w // 2, spec.h - 3 - spec.thigh - spec.shin)
    hx = hip_xy[0] + pose.hip[0]
    hy = hip_xy[1] + pose.hip[1]

    us, uc = _sc(pose.lean)
    up = (us, -uc)             # torso direction (hip -> neck)
    fwd = (uc, us)             # facing direction, perpendicular to `up`
    nx = hx + up[0] * spec.torso
    ny = hy + up[1] * spec.torso
    sx = nx - up[0] * 1.0      # shoulder sits just below the neck
    sy = ny - up[1] * 1.0

    joints = {"hip": (hx, hy), "neck": (nx, ny), "up": up, "fwd": fwd}

    def leg(angles, colour_thigh, colour_shin, shoe, far):  # noqa: ARG001
        a, k = angles
        s1, c1 = _sc(a)
        kx = hx + s1 * spec.thigh
        ky = hy + c1 * spec.thigh
        s2, c2 = _sc(a - k)
        ax = kx + s2 * spec.shin
        ay = ky + c2 * spec.shin
        g.seg(hx, hy, kx, ky, spec.leg_w, colour_thigh)
        g.seg(kx, ky, ax, ay, spec.leg_w, colour_shin)
        # foot points "forward" relative to the shin
        fx = ax + c2 * spec.foot
        fy = ay - s2 * spec.foot
        g.seg(ax, ay, fx, fy, spec.leg_w, shoe)
        return (ax, ay), (fx, fy)

    def arm(angles, colour_upper, colour_fore):
        a, e = angles
        s1, c1 = _sc(a)
        ex = sx + s1 * spec.upper
        ey = sy + c1 * spec.upper
        s2, c2 = _sc(a + e)
        wx = ex + s2 * spec.fore
        wy = ey + c2 * spec.fore
        g.seg(sx, sy, ex, ey, spec.arm_w, colour_upper)
        g.seg(ex, ey, wx, wy, spec.arm_w, colour_fore)
        return (wx, wy), (ex, ey)

    # far side first, drawn darker
    hand_b, elbow_b = arm(pose.ab, _dark(spec.uppers), _dark(spec.forearms))
    leg(pose.lb, _dark(spec.thighs), _dark(spec.shins), SHOE, True)

    # torso
    g.seg(hx, hy, nx, ny, spec.torso_w, TOP)
    if spec.belt:
        g.seg(hx + up[0] * 1.2 - fwd[0] * 2, hy + up[1] * 1.2 - fwd[1] * 2,
              hx + up[0] * 1.2 + fwd[0] * 2, hy + up[1] * 1.2 + fwd[1] * 2, 1, spec.belt)
    if spec.skirt:
        for i in range(3):
            w = 2 + i
            cx = hx - up[0] * i
            cy = hy - up[1] * i
            g.seg(cx - fwd[0] * w, cy - fwd[1] * w, cx + fwd[0] * w, cy + fwd[1] * w, 1, TOP)

    foot_f, toe_f = leg(pose.lf, spec.thighs, spec.shins, SHOE, False)

    # head
    r = spec.head_r
    cx = nx + up[0] * (r + 0.6)
    cy = ny + up[1] * (r + 0.6)
    joints["head"] = (cx, cy)
    g.disc(cx, cy, r, SKIN)
    # Classify each head pixel in head-local coordinates (u forward, v up).
    for yy in range(int(cy - r - 1), int(cy + r + 2)):
        for xx in range(int(cx - r - 1), int(cx + r + 2)):
            if g.get(xx, yy) != SKIN:
                continue
            dx = xx - cx
            dy = yy - cy
            u = dx * fwd[0] + dy * fwd[1]
            v = dx * up[0] + dy * up[1]
            c = SKIN
            if spec.hair == "long":
                if v > -0.2 or u < -0.6:
                    c = HAIR
            elif spec.hair == "short":
                if v > 0.9 or (u < -1.2 and v > -1.5):
                    c = HAIR
            elif spec.hair == "bald":
                if u < -1.6 and v > -1:
                    c = HAIR
            if spec.beard and v < 0.2 and u > -1.5 and not (v > -0.6 and u > 1.4):
                c = HAIR
            if spec.hat == "cap" and v > 0.6:
                c = ACC1
            elif spec.hat == "hood" and (v > 0.4 or u < -1.0):
                c = TOP
            elif spec.hat == "helmet" and (v > -0.5 or u < -0.5):
                c = ACC1
            if c != SKIN:
                g.set(xx, yy, c)

    def at(u, v):
        return cx + fwd[0] * u + up[0] * v, cy + fwd[1] * u + up[1] * v

    if spec.hat == "cap":
        for u in range(1, r + 3):
            px, py = at(u, 1)
            g.set(px, py, ACC2)
    if spec.hat == "hood":
        # Link-style pointed cap: a tail sweeping back and down
        px0, py0 = at(-r + 0.5, r - 0.5)
        px1, py1 = at(-r - 3.5, -1)
        g.seg(px0, py0, px1, py1, 2, TOP)
        px2, py2 = at(-r - 4.5, -2.5)
        g.set(px2, py2, TOP)
    if spec.hat == "helmet":
        px, py = at(1.6, 0.2)
        g.set(px, py, ACC2)
        px, py = at(2.4, 0.2)
        g.set(px, py, ACC2)
    if pose.eye:
        ex, ey = at(1.6, 0.1)
        if spec.hat != "helmet":
            g.set(ex, ey, EYE)
    else:
        ex, ey = at(1.2, -0.2)
        g.set(ex, ey, SKIN_D)
        ex, ey = at(2.0, -0.2)
        g.set(ex, ey, SKIN_D)
    if pose.mouth:
        mx, my = at(2.2, -1.6)
        g.set(mx, my, OUT)

    hand_f, elbow_f = arm(pose.af, spec.uppers, spec.forearms)
    joints["hand_f"] = hand_f
    joints["hand_b"] = hand_b
    joints["foot_f"] = foot_f
    joints["elbow_f"] = elbow_f

    if spec.extra:
        spec.extra(g, joints, pose)

    g.outline(OUT)
    return g


# ---------------------------------------------------------------- gait helpers

def gait(phase, stride, knee, arm, elbow, lean=0, bob=1.0):
    """A pose part-way (0..1) through a walk or run cycle."""
    p = phase * 2 * math.pi
    s = math.sin(p)
    # knee bends most while the leg swings forward (recovery)
    kf = knee * (0.15 + 0.85 * max(0.0, math.sin(p + 1.2)))
    kb = knee * (0.15 + 0.85 * max(0.0, math.sin(p + math.pi + 1.2)))
    lift = -abs(math.cos(p)) * bob
    return Pose(
        lean=lean,
        hip=(0, lift),
        lf=(stride * s, kf),
        lb=(-stride * s, kb),
        af=(-arm * s + lean * 0.5, elbow),
        ab=(arm * s + lean * 0.5, elbow),
    )


GAITS = {
    # name: stride, knee, arm swing, elbow bend, lean, bob
    "walk": (22, 28, 22, 25, 2, 0.6),
    "jog": (34, 62, 34, 70, 6, 1.0),
    "run": (44, 92, 46, 85, 12, 1.2),
    "sprint": (54, 115, 58, 95, 20, 1.5),
}


def cycle(spec, name, frames=8, **over):
    stride, knee, arm, elbow, lean, bob = GAITS[name]
    out = []
    for i in range(frames):
        pose = gait(i / frames, stride, knee, arm, elbow, lean, bob)
        for k in over:
            setattr(pose, k, over[k])
        out.append(render(spec, pose))
    return out


def stand(**kw):
    p = Pose(lf=(4, 2), lb=(-4, 2), af=(8, 12), ab=(-8, 12))
    for k in kw:
        setattr(p, k, kw[k])
    return p


def lying(**kw):
    # On its back, head to the left, face up.
    p = Pose(lean=-90, lf=(88, 4), lb=(92, -2), af=(80, 6), ab=(96, 0), eye=False)
    for k in kw:
        setattr(p, k, kw[k])
    return p


def sitting(**kw):
    p = Pose(lean=-2, lf=(84, 84), lb=(80, 80), af=(30, 60), ab=(20, 60))
    for k in kw:
        setattr(p, k, kw[k])
    return p
