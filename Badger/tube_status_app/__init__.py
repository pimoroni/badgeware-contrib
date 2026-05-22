import urequests as requests
import wifi
import time

wifi.connect()
title = rect(0,0,264,20)
tubes = rect(0, 20, 264, 176)
def update():
    if wifi.connect():
        for _ in range(3):
            badge.caselights(1)
            time.sleep(0.1)
            badge.caselights(0)
            time.sleep(0.1)
        url = "https://api.tfl.gov.uk/Line/Mode/tube/Status"
        response = requests.get(url)
        data = response.json()
        screen.pen = color.white
        screen.clear()
        screen.pen = color.black
        message = "".join(
        f"{line['name']}: {line['lineStatuses'][0]['statusSeverityDescription']}\n"
        for line in data
        )
        screen.font = rom_font.unfair
        text.draw(screen, "Tube Status", title)
        line = shape.line(0, 15, 264, 15, 2)
        line2 = shape.line(0, 20, 264, 20, 2)
        screen.shape(line)
        screen.shape(line2)
        for i in range(screen.width / 8):
            x = 8 * i
            screen.line(x, 15, x, 20)
        screen.font = rom_font.nope
        text.draw(screen, message, tubes)
        badge.update()
        time.sleep(300)
    else:
        screen.pen = color.white
        screen.clear()
        screen.pen = color.black
        text.draw(screen, "No Wi-Fi connection", title)
        badge.update()
        badge.caselights(1)
        time.sleep(1)
        wifi.tick() 
run(update)
