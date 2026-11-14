import time
badge.mode(LORES | VSYNC)

selected_light = 0

def update():
    screen.pen = color.white
    screen.clear()

for _i in range(16):
    selected_light = (selected_light - 1) % 4
    levels = list(badge.caselights())
    levels[selected_light] = (levels[selected_light] + 0.25) % 1.25
    badge.caselights(*levels)
    time.sleep(0.1)
run(update)
