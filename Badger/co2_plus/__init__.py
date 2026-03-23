import breakout_scd41
from machine import I2C
import sys
import os

sys.path.insert(0, "/system/apps/co2_plus")
os.chdir("/system/apps/co2_plus")
mona_sans = font.load("/system/assets/fonts/MonaSans-Medium.af")
screen.antialias = image.X4

import ui

try:
    breakout_scd41.init(I2C())
    breakout_scd41.start()
except RuntimeError:
    fatal_error("Error!", "Unable to init the SCD41. Check your connection and try again")

# rects for the windows we'll draw later
c_win = rect(10, 25, screen.width - 20, 75)
th_win = rect(10, 110, screen.width - 20, 60)


def update():

    screen.pen = color.white
    screen.clear()

    # wait for the sensor to be ready and get the data
    ui.draw_alert("Getting reading from SCD41 Sensor")
    try:
        while not breakout_scd41.ready():
            pass
        co2, temperature, humidity = breakout_scd41.measure()
    except RuntimeError:
        fatal_error("Error!", "Unable to get readings from the SCD41. Check your connection and try again")

    # draw the windows and headers
    ui.draw_header("C02 Plus", rect(0, 0, screen.width, screen.height))
    ui.draw_window(c_win)
    ui.draw_header("C02", c_win)
    ui.draw_window(th_win)
    ui.draw_header("Temperature/Humidity", th_win)

    # we're using a vector font to draw the PPM so we can make it larger
    screen.font = mona_sans
    size = 54
    co2_text = f"{co2:,} PPM"
    w, h = screen.measure_text(co2_text, size)
    x, y = c_win.x + (c_win.w // 2) - (w / 2), c_win.y + 8
    text.draw(screen, co2_text, rect(x - 2, y, w + 10, h), size=size)

    # draw the temperature and humidity in a pixel font
    screen.font = rom_font.ignore
    th_text = f"{temperature:.1f}°C   |   {humidity:.1f}%"
    w, _ = screen.measure_text(th_text)
    x, y = th_win.x + (th_win.w // 2) - (w / 2) + 8, th_win.y + 20
    screen.text(th_text, x, y)

    # wake up again in 30 minutes to refresh the data
    rtc.set_alarm(minutes=5)

    badge.mode(MEDIUM_UPDATE)
    badge.update()
    badge.sleep()

run(update)
