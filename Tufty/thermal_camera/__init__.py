import os
import sys

from machine import I2C
from ulab import numpy

badge.mode(HIRES)

# Standalone bootstrap for finding app assets
os.chdir("/system/apps/thermal_camera")

# Standalone bootstrap for module imports
sys.path.insert(0, "/system/apps/thermal_camera")

from mlx90640 import MLX90640, RefreshRate, init_float_array

try:
    # init the camera and set the refresh rate
    mlx = MLX90640(I2C(freq=1_000_000))
    mlx.refresh_rate = RefreshRate.REFRESH_16_HZ
except ValueError as e:
    fatal_error("I/O Error",
                 f"\n{e}\n\nMLX90640 not detected. Check your connection and try again.")

# inferno palette
PALETTE = [[0, 0, 0], [0, 0, 0], [1, 0, 4], [5, 2, 14], [14, 4, 31], [27, 5, 51], [35, 5, 58],
           [44, 7, 62], [54, 10, 65], [63, 13, 67], [72, 16, 68], [82, 19, 69], [93, 23, 68],
           [104, 27, 67], [115, 31, 65], [126, 35, 62], [138, 41, 57], [149, 48, 52], [160, 55, 47],
           [171, 64, 41], [182, 76, 33], [191, 87, 26], [200, 100, 18], [207, 114, 10], [214, 131, 5],
           [220, 147, 11], [224, 164, 25], [228, 182, 43], [229, 203, 68], [231, 222, 96], [237, 239, 130], [252, 254, 164]]


raw_frame = init_float_array(768)
show_osd = True
show_h_flipped = False
show_v_flipped = True

def draw_osd(low, high):
    x = screen.width - 25
    y = 40

    screen.pen = color.rgb(0, 0, 0, 150)
    screen.rectangle(x - 10, y - 15, 30, screen.height - 50)

    screen.pen = color.white
    screen.text(f"{high:.1f}", x - 6, y - 15)
    screen.text(f"{low:.1f}", x - 6, y + 160)

    for c in reversed(PALETTE):
        screen.pen = color.rgb(*c)
        screen.rectangle(x, y, 10, 5)
        y += 5

def update():
    global show_osd, show_h_flipped, show_v_flipped, frame

    if badge.pressed(BUTTON_B):
        show_osd = not show_osd

    if badge.pressed(BUTTON_A) or badge.pressed(BUTTON_C):
        show_h_flipped = not show_h_flipped

    if badge.pressed(BUTTON_UP) or badge.pressed(BUTTON_DOWN):
        show_v_flipped = not show_v_flipped

    try:
        # Get the frame data from the MLX90640
        mlx.get_frame(raw_frame)
        frame = numpy.array(raw_frame)

        # Get the highest and lowest temperature values from the frame
        low = numpy.min(frame)
        high = numpy.max(frame)

        # map the temperature values to our palette and reshape to a 2D array
        frame -= low
        frame /= high - low
        frame *= len(PALETTE) - 1
        frame = frame.reshape((24, 32))

        # flip!
        if show_v_flipped:
            frame = numpy.flip(frame, axis=0)

        if show_h_flipped:
            frame = numpy.flip(frame, axis=1)

        # draw the 'pixels'
        # each pixel from the camera is drawn as a 10x10 rectangle
        for y, row in enumerate(frame):
            for x, pixel in enumerate(row):
                # set the pen and draw the 'pixel'
                screen.pen = color.rgb(*PALETTE[int(pixel)])
                screen.rectangle(x * 10, y * 10, 10, 10)

        if show_osd:
            draw_osd(low, high)

    except RuntimeError:
        pass
    except ValueError:
        pass
    except OSError as e:
        fatal_error("Device Error",
                    f"\n{e}\n\nAn error occurred and the app was forced to stop. Check your MLX90640 connection and try again.")

run(update)
