import math
import os
import random
import sys
import time

from lsm6ds3 import LSM6DS3, NORMAL_MODE_104HZ
from machine import I2C

ANSWERS = ["Yes", "Yes, without doubt", "You may rely on it", "As I see it, yes",
           "Most likely", "No", "My sources say no", "Outlook not so good",
           "Unsure", "Ask again later", "Cannot predict now",
           "Don't count on it", "My reply is no", "Yes, in due time"
           ]

try:
    motion_sensor = LSM6DS3(I2C(), mode=NORMAL_MODE_104HZ)
except OSError:
    motion_sensor = None

badge.mode(HIRES)
badge.antialias = image.X4

# Standalone bootstrap for finding app assets
os.chdir("/system/apps/magic_ball")

# Standalone bootstrap for module imports
sys.path.insert(0, "/system/apps/magic_ball")

CENTRE_X, CENTRE_Y = screen.width / 2, screen.height / 2
PURPLE = color.rgb(200, 0, 200)
SHADOW = color.rgb(89, 125, 206, 55)
BLACK = color.rgb(0, 0, 0)
BLUE = color.rgb(25, 25, 100)


class Ball:

    MAX_DISTANCE = 300

    def __init__(self):
        self.angle = random.uniform(0, 2 * math.pi)
        self.distance = random.uniform(1, Ball.MAX_DISTANCE)
        self.color = color.rgb(0, 0, 60)
        self.rotation = random.uniform(0, 360)

    def draw(self):
        origin_x = screen.width // 2 + math.sin(time.ticks_ms() / 1000) * 50
        origin_y = screen.height // 2
        x = origin_x + math.cos(self.angle) * self.distance
        y = origin_y + math.sin(self.angle) * self.distance

        scale = self.distance / 5

        screen.pen = self.color
        screen.shape(shape.circle(x, y, scale).stroke(2))

    def update(self):
        self.distance *= 1.1
        self.angle += 0.1
        self.rotation += 5
        if self.distance > Ball.MAX_DISTANCE:
            self.distance = random.uniform(1, 20)


balls = [Ball() for _ in range(20)]


screen.pen = color.rgb(0, 0, 0, 255)
screen.clear()

fade_start = 0
fade = False

selection = "Shake Me" if motion_sensor else "Press B"

# Function to center text. One word per line. Centered on the X and Y
def center_text(image, text, y_spacing):
    words = text.split()
    y = (image.height / 2) - ((len(words) * y_spacing) / 2)
    y += 5

    for word in words:
        word = word.upper()
        w, _ = image.measure_text(word)
        x = (image.width / 2) - (w / 2)
        image.text(word, x, y)
        y += y_spacing


def update():
    global fade, fade_start, selection

    screen.pen = BLACK
    screen.clear()

    die_image = image(150, 150)
    die_image.font = rom_font.nope

    for ball in balls:
        ball.update()
        ball.draw()

    screen.pen = color.rgb(0, 0, 50)
    screen.shape(shape.circle(CENTRE_X, CENTRE_Y, 107))

    if fade:
        speed = 255
        frame = badge.ticks - fade_start
        alpha = math.cos(frame / speed) * 255
        alpha = max(min(alpha, 255), 0)
        die_image.alpha = int(alpha)

        if frame > (speed * 6):
            fade = False

    # draw some shading for the viewport
    screen.pen = color.grey
    screen.shape(shape.circle(CENTRE_X - 2, CENTRE_Y - 2, 98).stroke(2))

    screen.pen = color.white
    screen.shape(shape.circle(CENTRE_X + 1, CENTRE_Y + 1, 98).stroke(2))

    # draw the middle of the viewport
    screen.pen = BLACK
    screen.shape(shape.circle(CENTRE_X, CENTRE_Y, 100))

    x, y = die_image.width / 2, die_image.height / 2
    die_image.pen = SHADOW
    die_image.shape(shape.regular_polygon(x, y, 60, 3).stroke(8))

    die_image.pen = color.blue
    die_image.shape(shape.regular_polygon(x, y, 62, 3))

    # only draw the text if the animation has finished
    if not fade:
        die_image.pen = color.rgb(255, 255, 255, 100)
        center_text(die_image, selection, 13)

    screen.blit(die_image, CENTRE_X - (die_image.width / 2), CENTRE_Y - (die_image.height / 2))

    try:
        if motion_sensor and motion_sensor.double_tap_detected() or badge.pressed(BUTTON_B):
            if not fade:
                # Trigger animation and change
                fade = True
                fade_start = badge.ticks
                selection = random.choice(ANSWERS)
    except OSError:
        fatal_error("I/O Error", "\nUnable to communicate with the Multi-Sensor Stick!\n\nCheck your connection and try again.")



run(update)

