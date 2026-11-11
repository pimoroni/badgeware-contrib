# ---------------------------------------------------------------
# Example: a simple badge with the Roving Eye as its idle screen
#
# Put this file in a folder such as /system/apps/hello/ as __init__.py,
# with eye.py next to it. After IDLE_SECONDS without a button press
# the eye takes over; any button brings the badge back.
# ---------------------------------------------------------------
import sys
import os

APP_DIR = "/system/apps/hello"     # change to your app's folder
sys.path.insert(0, APP_DIR)
os.chdir(APP_DIR)

import eye

NAME = "Hello!"
IDLE_SECONDS = 10 * 60             # 10 minutes

screen.antialias = screen.X2
W = screen.width
H = screen.height

BACKGROUND = color.rgb(34, 85, 51)
TEXT = color.rgb(255, 255, 255)

idle = False
last_press = None


def draw_badge():
    screen.pen = BACKGROUND
    screen.clear()
    screen.pen = TEXT
    w, h = screen.measure_text(NAME)
    screen.text(NAME, (W - w) / 2, (H - h) / 2)


def init():
    pass


def update():
    global idle, last_press

    now = badge.ticks
    if last_press is None:
        last_press = now

    a = badge.pressed(BUTTON_A)
    b = badge.pressed(BUTTON_B)
    c = badge.pressed(BUTTON_C)

    if a or b or c:
        last_press = now
        if idle:
            idle = False       # any button wakes the badge up
            a = b = c = False

    if not idle and now - last_press > IDLE_SECONDS * 1000:
        idle = True
        eye.reset(now)         # the eye wakes up from its nap

    if idle:
        eye.draw(now)
        return

    draw_badge()


def on_exit():
    pass


run(update)
