import breakout_scd41
import sys
import os
from pimoroni_i2c import PimoroniI2C

# we're using pimoroni_i2c here to work around a quirk of the scd41 library :')
i2c = PimoroniI2C(4, 5)

sys.path.insert(0, "/system/apps/co2_plus")
os.chdir("/system/apps/co2_plus")

screen.antialias = image.X4
screen.font = rom_font.absolute
display.set_brightness(0.05)


try:
    breakout_scd41.init(i2c)
    breakout_scd41.start()
except RuntimeError:
    fatal_error("Error!", "Unable to init the SCD41. Check your connection and try again")


class Page:
    CO2 = 0
    TEMPERATURE = 1
    HUMIDITY = 2


page = Page.CO2
updated = None
co2, temperature, humidity = 0, 0, 0


# Function to center text. One word per line. Centered on the X and Y
def center_text(image, text, y_spacing):
    words = text.split()
    y = -3
    for word in words:
        word = word.upper()
        w, _ = image.measure_text(word)
        x = (image.width / 2) - (w / 2)
        image.text(word, x, y)
        y += y_spacing


def update():
    global page, updated, co2, temperature, humidity

    if badge.pressed(BUTTON_C):
        page += 1
    if badge.pressed(BUTTON_A):
        page -= 1
    page %= 3

    # attempt to grab a reading every 60 seconds
    if updated is None or (badge.ticks - updated) / 1000 > 60:
        try:
            if breakout_scd41.ready():
                co2, temperature, humidity = breakout_scd41.measure()
                updated = badge.ticks
        except RuntimeError:
            fatal_error("Error!", "Unable to get readings from the SCD41. Check your connection and try again")

    screen.pen = color.rgb(0, 0, 0)
    screen.clear()
    screen.pen = color.white

    if page == Page.CO2:
        co2_text = f"{co2:,} PPM"
        center_text(screen, co2_text, 11)
    if page == Page.TEMPERATURE:
        temp_text = f"{temperature:.1f} °C"
        center_text(screen, temp_text, 11)
    if page == Page.HUMIDITY:
        temp_text = f"{humidity:.1f} %RH"
        center_text(screen, temp_text, 11)


run(update)
