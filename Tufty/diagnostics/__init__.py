import gc
import os


badge.mode(LORES | VSYNC)
screen.font = rom_font.sins

BG = color.rgb(12, 18, 28)
PANEL = color.rgb(25, 36, 52)
TEXT = color.rgb(225, 235, 245)
MUTED = color.rgb(125, 150, 175)
ACCENT = color.rgb(32, 205, 180)
WARN = color.rgb(255, 185, 60)
ACTIVE = color.rgb(255, 90, 100)

PAGE_NAMES = ("OVERVIEW", "POWER + LIGHT", "SYSTEM", "CLOCK", "BUTTONS", "CASE LIGHTS")
BUTTONS = (BUTTON_A, BUTTON_B, BUTTON_C, BUTTON_UP, BUTTON_DOWN, BUTTON_HOME)
BUTTON_NAMES = {
    BUTTON_A: "A",
    BUTTON_B: "B",
    BUTTON_C: "C",
    BUTTON_UP: "UP",
    BUTTON_DOWN: "DOWN",
    BUTTON_HOME: "HOME",
}

page = 0
light_samples = []
last_light_sample = 0
press_counts = {button: 0 for button in BUTTONS}
initial_caselights = badge.caselights()
selected_light = 0


def safe_value(call, fallback="?"):
    try:
        return call()
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
        return fallback


def bytes_text(value):
    if not isinstance(value, (int, float)):
        return str(value)
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    return f"{value / 1024:.1f} KB"


def short_text(value, width=22):
    value = str(value)
    if len(value) > width:
        return value[:width - 1] + "~"
    return value


def draw_header():
    screen.pen = PANEL
    screen.rectangle(0, 0, screen.width, 17)
    screen.pen = ACCENT
    screen.rectangle(0, 16, screen.width, 1)
    screen.pen = TEXT
    screen.text(PAGE_NAMES[page], 5, 3)
    screen.pen = MUTED
    screen.text(f"{page + 1}/{len(PAGE_NAMES)}", 137, 3)


def draw_footer(note="UP/DOWN: pages"):
    screen.pen = PANEL
    screen.rectangle(0, 105, screen.width, 15)
    screen.pen = MUTED
    screen.text(note, 5, 108)


def draw_row(label, value, y, value_colour=TEXT):
    screen.pen = MUTED
    screen.text(label, 5, y)
    screen.pen = value_colour
    screen.text(short_text(value), 62, y)


def storage_values(path):
    values = safe_value(lambda: badge.disk_free(path), None)
    if not values:
        return "unavailable"
    total, used, free = values
    return f"{bytes_text(used)} / {bytes_text(total)}"


def update_light_samples():
    global last_light_sample

    if badge.ticks - last_light_sample >= 100:
        light_samples.append(safe_value(badge.light_level, 0))
        del light_samples[:-55]
        last_light_sample = badge.ticks


def draw_overview():
    battery = safe_value(badge.battery_level)
    voltage = safe_value(badge.battery_voltage)
    light = safe_value(badge.light_level)
    draw_row("Battery", f"{battery}%", 23, ACCENT if battery != "?" and battery > 20 else WARN)
    draw_row("Voltage", f"{voltage:.3f} V" if isinstance(voltage, float) else voltage, 35)
    draw_row("USB", safe_value(badge.usb_connected), 47)
    draw_row("Charging", safe_value(badge.is_charging), 59)
    draw_row("Ambient", light, 71)
    draw_row("Uptime", f"{badge.ticks / 1000:.1f} s", 83)
    draw_row("Frame", f"{badge.ticks_delta} ms", 95)


def draw_power_light():
    battery = safe_value(badge.battery_level, 0)
    light = safe_value(badge.light_level, 0)

    screen.pen = MUTED
    screen.text(f"Battery {battery}%   Light {light}", 5, 22)

    graph_x = 5
    graph_y = 39
    graph_w = 150
    graph_h = 53
    screen.pen = PANEL
    screen.rectangle(graph_x, graph_y, graph_w, graph_h)

    if light_samples:
        low = min(light_samples)
        high = max(light_samples)
        span = max(1, high - low)
        screen.pen = ACCENT
        last_x = graph_x
        last_y = graph_y + graph_h - 1
        for index, sample in enumerate(light_samples):
            x = graph_x + index * (graph_w - 1) / max(1, len(light_samples) - 1)
            y = graph_y + graph_h - 1 - ((sample - low) / span) * (graph_h - 2)
            screen.shape(shape.line(last_x, last_y, x, y, 1))
            last_x, last_y = x, y
        screen.pen = MUTED
        screen.text(f"min {low}  max {high}", 8, 79)


def draw_system():
    uname = safe_value(os.uname, None)
    platform = uname.sysname if uname and hasattr(uname, "sysname") else "MicroPython"
    release = uname.release if uname and hasattr(uname, "release") else "?"
    resolution = f"{badge.resolution[0]} x {badge.resolution[1]}"
    ram_free = safe_value(gc.mem_free)
    ram_used = safe_value(gc.mem_alloc)

    draw_row("Platform", platform, 23)
    draw_row("Release", release, 35)
    draw_row("UID", badge.uid, 47)
    draw_row("Display", resolution, 59)
    draw_row("RAM free", bytes_text(ram_free), 71)
    draw_row("RAM used", bytes_text(ram_used), 83)
    draw_row("System", storage_values("/system"), 95)


def draw_clock():
    dt = safe_value(rtc.datetime, None)
    if dt and len(dt) >= 7:
        year, month, day, hour, minute, second, dow = dt
        date_text = f"{year:04d}-{month:02d}-{day:02d}"
        time_text = f"{hour:02d}:{minute:02d}:{second:02d}"
    else:
        date_text = time_text = "unavailable"
        dow = "?"

    wake = "button" if safe_value(badge.woken_by_button, False) else "reset" if safe_value(badge.woken_by_reset, False) else "other"
    draw_row("Date", date_text, 23)
    draw_row("Time", time_text, 35)
    draw_row("Weekday", dow, 47)
    draw_row("Alarm", safe_value(rtc.alarm_status), 59)
    draw_row("Woke by", wake, 71)
    draw_row("Ticks", badge.ticks, 83)
    draw_row("Delta", badge.ticks_delta, 95)


def button_list(values):
    names = [BUTTON_NAMES.get(button, "?") for button in values]
    return " ".join(names) if names else "-"


def draw_buttons():
    draw_row("Held", button_list(badge.held()), 23, ACTIVE)
    draw_row("Pressed", button_list(badge.pressed()), 35, ACCENT)
    draw_row("Released", button_list(badge.released()), 47)
    draw_row("Changed", button_list(badge.changed()), 59)

    screen.pen = MUTED
    screen.text("Press counts", 5, 73)
    x = 5
    y = 86
    for button in BUTTONS:
        screen.pen = ACTIVE if badge.held(button) else TEXT
        screen.text(f"{BUTTON_NAMES[button]}:{press_counts[button]}", x, y)
        x += 34 if button in (BUTTON_UP, BUTTON_DOWN, BUTTON_HOME) else 25


def draw_case_lights():
    levels = badge.caselights()
    screen.pen = MUTED
    screen.text("A/C: select   B: cycle", 5, 22)

    for index, level in enumerate(levels):
        x = 8 + index * 39
        height = 50 * level
        screen.pen = PANEL
        screen.rectangle(x, 38, 28, 54)
        screen.pen = ACCENT if index == selected_light else TEXT
        screen.rectangle(x + 3, 89 - height, 22, height)
        screen.text(str(index + 1), x + 10, 94)


def handle_buttons():
    global page, selected_light

    for button in badge.pressed():
        if button in press_counts:
            press_counts[button] += 1

    if badge.pressed(BUTTON_UP):
        page = (page - 1) % len(PAGE_NAMES)
    if badge.pressed(BUTTON_DOWN):
        page = (page + 1) % len(PAGE_NAMES)

    if page == 5:
        if badge.pressed(BUTTON_A):
            selected_light = (selected_light - 1) % 4
        if badge.pressed(BUTTON_C):
            selected_light = (selected_light + 1) % 4
        if badge.pressed(BUTTON_B):
            levels = list(badge.caselights())
            levels[selected_light] = (levels[selected_light] + 0.25) % 1.25
            badge.caselights(*levels)


def on_exit():
    badge.caselights(*initial_caselights)


def update():
    handle_buttons()
    update_light_samples()

    screen.pen = BG
    screen.clear()
    draw_header()

    if page == 0:
        draw_overview()
    elif page == 1:
        draw_power_light()
    elif page == 2:
        draw_system()
    elif page == 3:
        draw_clock()
    elif page == 4:
        draw_buttons()
    else:
        draw_case_lights()

    draw_footer("UP/DOWN: pages")


run(update)
