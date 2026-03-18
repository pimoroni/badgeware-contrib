import os
import sys

from lsm6ds3 import LSM6DS3, PERFORMANCE_MODE_416HZ
from machine import I2C

try:
    motion_sensor = LSM6DS3(I2C(), mode=PERFORMANCE_MODE_416HZ)
except OSError:
    fatal_error("Multi-Sensor Stick not found!", "\nThis app requires the Multi-Sensor Stick to function.\n\nPlease connect your Multi-Sensor Stick to the QW/ST connector on the back of your badge and relaunch the app.")

badge.mode(HIRES)
badge.antialias = image.X4

# Standalone bootstrap for finding app assets
os.chdir("/system/apps/spirit_level")

# Standalone bootstrap for module imports
sys.path.insert(0, "/system/apps/spirit_level")

CENTRE_X, CENTRE_Y = screen.width / 2, screen.height / 2

samples = []

level = rect(40, 20, screen.width - 80, 70)

screen.font = rom_font.futile
BACKGROUND = color.rgb(238, 170, 2)

def update():

    global samples

    # get the sensor readings
    try:
        _, ay, _, _, _, _ = motion_sensor.get_readings()
    except OSError:
        fatal_error("I/O Error", "\nUnable to communicate with the Multi-Sensor Stick!\n\nCheck your connection and try again.")

    # map to a range of -1.0 to 1.0.
    n = round((((ay - -16383.5) * (1.0 - -1.0)) / (16383.5 - -16383.5)) + -1.0, 1)

    # add our latest value to our samples list and cap it at max 20 values
    samples.append(n)
    samples = samples[-10:]

    # reset clip
    screen.clip = rect(0, 0, screen.width, screen.height)

    screen.pen = BACKGROUND
    screen.clear()

    # draw the surround
    screen.pen = color.black
    screen.shape(shape.rounded_rectangle(level.x - 25, 0, level.w + 50, screen.height - 100, 0, 0, 8, 8))
    screen.pen = color.smoke
    screen.shape(shape.rounded_rectangle(level.x, 0, level.w, screen.height - 130, 0, 0, 8, 8))

    # draw the main body of the spirit level
    screen.pen = color.rgb(176, 210, 26, 150)
    screen.shape(shape.rectangle(level.x, level.y, level.w, level.h))

    # draw the logo
    screen.alpha = 150
    screen.pen = color.black
    screen.shape(shape.circle(CENTRE_X + 3, CENTRE_Y + 73, 40))
    screen.shape(shape.circle(CENTRE_X, CENTRE_Y + 70, 40).stroke(2))
    screen.pen = BACKGROUND
    screen.shape(shape.circle(CENTRE_X, CENTRE_Y + 70, 40))
    screen.alpha = 255
    screen.pen = color.black

    # centre logo text
    logo_text = "TUFTY"
    w, _ = screen.measure_text(logo_text)
    x = CENTRE_X - (w / 2)
    screen.text(logo_text, x, CENTRE_Y + 56)

    # get the average from our samples
    offset = sum(samples) / len(samples)
    offset *= level.w / 2

    # set the clip and draw the bubble
    screen.clip = level
    screen.pen = color.rgb(255, 255, 255, 75)
    screen.circle(CENTRE_X + offset, level.y - 15, 38)

    # lines
    screen.pen = color.black
    screen.line(level.x + 80, level.y, level.x + 80, level.y + level.h)
    screen.line(level.x + 160, level.y, level.x + 160, level.y + level.h)
    screen.line(level.x + 75, level.y, level.x + 75, level.y + level.h)
    screen.line(level.x + 165, level.y, level.x + 165, level.y + level.h)

    # shadow and highlights
    screen.pen = color.rgb(0, 0, 0, 75)
    screen.shape(shape.rectangle(level.x, (level.y + level.h) - 5, level.w, 5))
    screen.pen = color.rgb(255, 255, 255, 75)
    screen.shape(shape.rectangle(level.x, level.y, level.w, 5))


run(update)
