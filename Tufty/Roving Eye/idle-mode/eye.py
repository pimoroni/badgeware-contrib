# ---------------------------------------------------------------
# The Roving Eye - idle screen for the badge app
#
# It darts about, scans the room, gets suspicious, blinks, and now
# and then stares straight at whoever is reading your badge.
# The badge app calls eye.reset() when it goes idle and eye.draw()
# every frame while idle.
# ---------------------------------------------------------------
import math
import random

W = screen.width     # 160
H = screen.height    # 120
CX = W / 2
CY = H / 2

# ---------------------------------------------------------------
# Colours
# ---------------------------------------------------------------
# Plain black around the eye, so it floats in the dark.
# For the forest green lids instead, use these two lines:
#   LID = color.rgb(34, 85, 51)
#   LID_CREASE = color.rgb(20, 55, 32)
LID = color.rgb(0, 0, 0)
LID_CREASE = LID
LID_SHADOW = color.rgb(90, 80, 70, 110)
LASH = color.rgb(12, 24, 14)
SCLERA = color.rgb(240, 236, 224)
SCLERA_EDGE = color.rgb(205, 190, 180)
IRIS_RING = color.rgb(10, 38, 20)
IRIS = color.rgb(40, 118, 68)
IRIS_INNER = color.rgb(176, 160, 70, 190)   # golden fleck around the pupil
STREAK = color.rgb(16, 64, 36, 150)
PUPIL = color.rgb(4, 4, 4)
GLINT = color.rgb(255, 255, 255)

# ---------------------------------------------------------------
# Eye geometry
# ---------------------------------------------------------------
EYE_HW = 74          # half the width of the eye opening
OPEN_TOP = 40        # how far the upper lid sits above centre
OPEN_BOT = 34        # how far the lower lid sits below centre
IRIS_R = 27
PUPIL_R = 10
RANGE_X = 44         # how far the iris can roam
RANGE_Y = 14
BLINK_MS = 170
QUICK_BLINK_MS = 110

# waking up: (time in ms from start, what happens)
WAKE_CLOSED = 700        # lids stay shut this long
WAKE_DROWSY = 2400       # by now the lids have slowly opened halfway
WAKE_BLINKS = (2700, 2950, 3200)   # quick blinks to shake off sleep
WAKE_DONE = 3900         # fully awake and roving after this

STREAKS = [i * math.pi * 2 / 18 + random.uniform(-0.1, 0.1) for i in range(18)]


class Eye:
    x = 0.0              # where the iris is now (offset from centre)
    y = 0.0
    tx = 0.0             # where it is heading
    ty = 0.0
    snap = 0.025         # how quickly it moves (bigger = snappier)
    mode = "dart"
    mode_until = 0
    dwell_until = 0
    scan = None          # (from_x, to_x, y, start, length) while scanning
    open = 1.0
    open_target = 1.0
    pupil = PUPIL_R
    pupil_target = PUPIL_R
    blink_start = -1000
    blink_len = BLINK_MS
    wake_start = 0
    next_blink = 1500
    double_blink = False
    last = None


# ---------------------------------------------------------------
# Light sensor (optional)
# ---------------------------------------------------------------
# Reads the LTR-559 light sensor on Pimoroni's Multi-Sensor Stick
# (plugged into the I2C port on the back). With no sensor plugged in,
# the eye behaves exactly as normal.
#
#   bright light   -> pupil shrinks      dim room   -> pupil widens
#   sudden flash   -> squint and blink   lights low -> drowsy lids
#   dark for a while -> dozes off, and wakes up when the light returns
DARK_LUX = 3            # this dark or darker counts as "lights out"
BRIGHT_LUX = 2000       # this bright or brighter shrinks the pupil fully
FLASH_JUMP = 4          # suddenly this many times brighter = a flash
SLEEP_AFTER_MS = 5000   # how long it has to stay dark before dozing off

try:
    from machine import I2C
    from breakout_ltr559 import BreakoutLTR559
    _sensor = BreakoutLTR559(I2C())
except Exception:
    _sensor = None


class Light:
    ok = _sensor is not None
    lux = None           # smoothed reading
    level = 0.5          # 0 = dark, 1 = bright
    next_read = 0
    dark_since = None


def read_lux():
    try:
        reading = _sensor.get_reading()
    except Exception:
        return None
    return None if reading is None else reading[-1]


def sense_light(now):
    if not Light.ok or now < Light.next_read:
        return
    Light.next_read = now + 100          # ten readings a second is plenty
    lux = read_lux()
    if lux is None:
        return
    if Light.lux is None:
        Light.lux = lux

    flash = lux > 60 and lux > Light.lux * FLASH_JUMP
    Light.lux = lux if flash else Light.lux + (lux - Light.lux) * 0.15

    lo, hi = math.log(DARK_LUX + 1), math.log(BRIGHT_LUX + 1)
    Light.level = min(1.0, max(0.0, (math.log(Light.lux + 1) - lo) / (hi - lo)))

    if flash and Eye.mode not in ("asleep", "waking"):
        start_mode(now, "dazzled")

    if Light.level <= 0.0:
        if Light.dark_since is None:
            Light.dark_since = now
        if Eye.mode != "asleep" and now - Light.dark_since > SLEEP_AFTER_MS:
            start_mode(now, "asleep")
    else:
        Light.dark_since = None
        if Eye.mode == "asleep" and Light.level > 0.15:
            start_mode(now, "waking")


def pupil_goal():
    # the mood sets the pupil size, the light shifts it up or down
    goal = Eye.pupil_target
    if Light.ok:
        goal += 4 - 8 * Light.level      # dark: +4, bright: -4
    return min(PUPIL_R + 5, max(4, goal))


def open_goal():
    # in dim light the lids get heavy
    if not Light.ok:
        return Eye.open_target
    return Eye.open_target * (0.6 + 0.4 * min(1.0, Light.level / 0.3))


# ---------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------
def random_spot():
    a = random.uniform(0, math.pi * 2)
    r = math.sqrt(random.random())
    return math.cos(a) * r * RANGE_X, math.sin(a) * r * RANGE_Y


def blink(now, length=BLINK_MS):
    Eye.blink_start = now
    Eye.blink_len = length
    Eye.double_blink = random.random() < 0.15
    Eye.next_blink = now + random.randint(1800, 5500)


def start_mode(now, mode=None):
    if mode is None:
        r = random.random()
        if r < 0.58:
            mode = "dart"
        elif r < 0.76:
            mode = "scan"
        elif r < 0.89:
            mode = "suspicious"
        elif r < 0.96:
            mode = "stare"
        else:
            mode = "startled"

    Eye.mode = mode
    if mode == "waking":
        Eye.wake_start = now
        Eye.x, Eye.y = 0.0, 4.0          # resting gaze, a little low
        Eye.tx, Eye.ty = 0.0, 4.0
        Eye.open = Eye.open_target = 0.0
        Eye.pupil = Eye.pupil_target = PUPIL_R + 4
        Eye.snap = 0.004
        Eye.scan = None
        Eye.blink_start = -1000
        Eye.double_blink = False
        Eye.next_blink = now + WAKE_DONE + random.randint(1500, 3500)
        Eye.mode_until = now + WAKE_DONE
        return

    Eye.open_target = 1.0
    Eye.pupil_target = PUPIL_R
    Eye.snap = 0.025
    Eye.scan = None

    if mode == "dart":
        Eye.mode_until = now + random.randint(2500, 6000)
        Eye.dwell_until = now

    elif mode == "scan":
        side = random.choice((-1, 1))
        length = random.randint(1800, 2800)
        Eye.scan = (-RANGE_X * side, RANGE_X * side,
                    random.uniform(-RANGE_Y, RANGE_Y) * 0.5, now + 250, length)
        Eye.tx, Eye.ty = Eye.scan[0], Eye.scan[2]
        Eye.mode_until = now + 250 + length + 400

    elif mode == "suspicious":
        Eye.open_target = 0.42
        Eye.pupil_target = PUPIL_R - 2
        Eye.snap = 0.004
        Eye.tx = RANGE_X * random.choice((-1, 1))
        Eye.ty = random.uniform(-3, 3)
        Eye.dwell_until = now + random.randint(900, 1400)
        Eye.mode_until = now + random.randint(2200, 3200)

    elif mode == "stare":
        Eye.tx, Eye.ty = 0, 0
        Eye.pupil_target = PUPIL_R + 3
        Eye.mode_until = now + random.randint(1500, 2600)

    elif mode == "asleep":
        Eye.open_target = 0.0
        Eye.tx, Eye.ty = 0.0, 4.0
        Eye.snap = 0.002
        Eye.mode_until = now + 3600000   # until the light comes back

    elif mode == "dazzled":
        Eye.open_target = 0.3
        Eye.pupil = 4                    # snaps small straight away
        Eye.pupil_target = PUPIL_R - 3
        Eye.tx = random.choice((-1, 1)) * 12
        Eye.ty = 5
        Eye.snap = 0.03
        blink(now, QUICK_BLINK_MS)
        Eye.mode_until = now + 1600

    elif mode == "startled":
        Eye.tx, Eye.ty = 0, -2
        Eye.open_target = 1.18
        Eye.pupil_target = PUPIL_R - 4
        Eye.snap = 0.05
        Eye.mode_until = now + 1000


def wake_up(now, dt):
    t = now - Eye.wake_start
    if t < WAKE_CLOSED:
        Eye.open = 0.0
    elif t < WAKE_DROWSY:
        # slow, sleepy opening that eases in
        p = (t - WAKE_CLOSED) / (WAKE_DROWSY - WAKE_CLOSED)
        Eye.open = 0.5 * p * p * (3 - 2 * p)
        Eye.pupil_target = PUPIL_R + 3
    else:
        Eye.open_target = 1.0 if t > WAKE_BLINKS[-1] else 0.55
        Eye.open += (Eye.open_target - Eye.open) * min(1.0, dt * 0.01)
        Eye.pupil_target = PUPIL_R
        Eye.ty = 0.0
        for b in WAKE_BLINKS:
            if b <= t < b + dt + 1 and now - Eye.blink_start > QUICK_BLINK_MS:
                blink(now, QUICK_BLINK_MS)
                Eye.next_blink = now + 4000
                Eye.double_blink = False
    k = min(1.0, dt * Eye.snap)
    Eye.x += (Eye.tx - Eye.x) * k
    Eye.y += (Eye.ty - Eye.y) * k
    Eye.pupil += (pupil_goal() - Eye.pupil) * min(1.0, dt * 0.003)


def behave(now, dt):
    sense_light(now)
    if Eye.mode == "asleep":
        Eye.open += (0.0 - Eye.open) * min(1.0, dt * 0.0015)   # slow doze
        Eye.x += (Eye.tx - Eye.x) * min(1.0, dt * Eye.snap)
        Eye.y += (Eye.ty - Eye.y) * min(1.0, dt * Eye.snap)
        Eye.next_blink = now + 1000
        return
    if Eye.mode == "waking" and now < Eye.mode_until:
        wake_up(now, dt)
        return
    if now >= Eye.mode_until:
        if random.random() < 0.35:
            blink(now)
        start_mode(now)

    if Eye.mode == "dart" and now >= Eye.dwell_until:
        Eye.tx, Eye.ty = random_spot()
        Eye.pupil_target = PUPIL_R + random.uniform(-1.5, 1.5)
        Eye.dwell_until = now + random.randint(250, 1400)

    elif Eye.mode == "suspicious" and now >= Eye.dwell_until:
        Eye.tx = -Eye.tx              # shifty look to the other side
        Eye.dwell_until = Eye.mode_until + 1

    if Eye.scan:
        x0, x1, sy, start, length = Eye.scan
        t = min(1.0, max(0.0, (now - start) / length))
        t = t * t * (3 - 2 * t)       # ease in and out
        Eye.tx = x0 + (x1 - x0) * t
        Eye.ty = sy
        Eye.x += (Eye.tx - Eye.x) * min(1.0, dt * 0.02)
        Eye.y += (Eye.ty - Eye.y) * min(1.0, dt * 0.02)
    else:
        k = min(1.0, dt * Eye.snap)
        Eye.x += (Eye.tx - Eye.x) * k
        Eye.y += (Eye.ty - Eye.y) * k

    Eye.open += (open_goal() - Eye.open) * min(1.0, dt * 0.008)
    Eye.pupil += (pupil_goal() - Eye.pupil) * min(1.0, dt * 0.006)

    if now >= Eye.next_blink:
        blink(now)
    if Eye.double_blink and now - Eye.blink_start > BLINK_MS + 90:
        Eye.double_blink = False
        Eye.blink_start = now
        Eye.blink_len = BLINK_MS
        Eye.next_blink = now + random.randint(1800, 5500)


def lid_closure(now):
    t = (now - Eye.blink_start) / Eye.blink_len
    if 0 <= t <= 1:
        return math.sin(t * math.pi)
    return 0.0


# ---------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------
def lid_curve(sign, amount, steps=20, x0=0, x1=W):
    # a parabola across the screen; past the eye corners it crosses
    # the other lid, so the two lids together make an almond shape
    pts = []
    for i in range(steps + 1):
        x = x0 + i * (x1 - x0) / steps
        u = (x - CX) / EYE_HW
        y = CY + sign * amount * (1 - u * u)
        pts.append((x, min(H, max(0, y))))   # keep every point on screen
    return pts


def fill_lid(sign, amount, pen):
    pts = lid_curve(sign, amount)
    edge = 0 if sign < 0 else H
    pts.append((W, edge))
    pts.append((0, edge))
    screen.pen = pen
    screen.shape(shape.custom([vec2(x, y) for x, y in pts]))


def stroke_curve(pts, thickness, pen):
    screen.pen = pen
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        screen.shape(shape.line(x1, y1, x2, y2, thickness))


def draw_iris(ix, iy, pupil):
    screen.pen = IRIS_RING
    screen.shape(shape.circle(ix, iy, IRIS_R))
    screen.pen = IRIS
    screen.shape(shape.circle(ix, iy, IRIS_R - 3))

    screen.pen = STREAK
    for a in STREAKS:
        c, s = math.cos(a), math.sin(a)
        screen.line(ix + c * (pupil + 3), iy + s * (pupil + 3),
                    ix + c * (IRIS_R - 4), iy + s * (IRIS_R - 4))

    screen.pen = IRIS_INNER
    screen.shape(shape.circle(ix, iy, pupil + 5))
    screen.pen = PUPIL
    screen.shape(shape.circle(ix, iy, pupil))

    screen.pen = GLINT
    screen.shape(shape.circle(ix - 8, iy - 9, 4))
    screen.shape(shape.circle(ix + 7, iy + 6, 1.5))


def draw_eye(now):
    # white of the eye, a little darker towards the corners
    screen.pen = SCLERA_EDGE
    screen.clear()
    screen.pen = SCLERA
    screen.shape(shape.circle(CX, CY, 58))

    draw_iris(CX + Eye.x, CY + Eye.y, Eye.pupil)

    # lids follow the gaze a little: looking up lifts the upper lid
    shut = 1 - lid_closure(now)
    top = max(0.0, (OPEN_TOP * Eye.open - Eye.y * 0.4) * shut)
    bot = max(0.0, (OPEN_BOT * Eye.open + Eye.y * 0.25) * shut)

    fill_lid(-1, top - 4, LID_SHADOW)   # soft shadow under the upper lid
    fill_lid(-1, top, LID)
    fill_lid(1, bot, LID)

    # crease above the eye, lash lines, and a few lashes
    left, right = CX - EYE_HW, CX + EYE_HW
    stroke_curve(lid_curve(-1, top + 9, 12, left + 14, right - 14), 1.5, LID_CREASE)
    upper = lid_curve(-1, top, 20, left, right)
    stroke_curve(upper, 3, LASH)
    stroke_curve(lid_curve(1, bot, 20, left, right), 1.5, LASH)
    screen.pen = LASH
    for i in range(4, 17, 2):
        x, y = upper[i]
        lean = (x - CX) / EYE_HW
        screen.shape(shape.line(x, y, x + lean * 5, y - 5, 1.5))


# ---------------------------------------------------------------
# Called from the badge app
# ---------------------------------------------------------------
def reset(now):
    # each time the badge goes idle the eye wakes up from sleep
    Eye.last = now
    start_mode(now, "waking")


def draw(now):
    if Eye.last is None:
        reset(now)
    dt = min(100, now - Eye.last)
    Eye.last = now
    behave(now, dt)
    draw_eye(now)
