# Burn Helper: live Claude Code activity and usage on a Pimoroni Tufty 2350.
#
# Polls the bridge on your Mac (bridge/burn_helper_bridge.py) over Wi-Fi and animates
# one of three themes by activity level, with hearts for the remaining usage.
#
# Buttons
#   A / C      on the animation: previous / next theme. In Desktop mode: step through the
#              sessions waiting for you. In Debug mode: turn pages (the last is Wi-Fi debug,
#              where UP picks a saved network to connect to)
#   B          animation -> Desktop mode -> Debug mode -> animation; hold 2 s for phone setup
#   hold UP    demo mode for 2 s (cycles every level, shows a DEMO tag)
#   DOWN       brightness: 10 levels, then 0% (screen off, badge still running), then full again;
#              hold 2 s to switch the case LEDs on or off (off by default)
#   HOME       switch to the stock app menu (HOME again comes back here)
#
# What the agents do (the bridge's activity feed) plays as short one-shot animations on top
# of the walk or run: a sword combo for an edit, a bomb for a command, and so on (see the
# themes' ACTIONS).

import gc
import math
import os
import sys
import time

APP_DIR = "/system/apps/burn_helper"
sys.path.insert(0, APP_DIR)
os.chdir(APP_DIR)

badge.mode(LORES | VSYNC)

import config  # noqa: E402
import gfx  # noqa: E402
import net  # noqa: E402
import scene as S  # noqa: E402
import usb  # noqa: E402
import views  # noqa: E402
import power  # noqa: E402

THEMES = ("hero", "gameshow", "chocolates")
LABELS = {"hero": "HYRULE", "gameshow": "RUNNING MAN", "chocolates": "FORREST"}
# 10 lit backlight levels, brightest first (steps roughly even to the eye), then 0%: the screen
# is off but the badge keeps running
BRIGHT = (1.0, 0.85, 0.7, 0.57, 0.46, 0.36, 0.28, 0.21, 0.15, 0.1, 0.0)
OFF = len(BRIGHT) - 1
SCREEN_OFF_NOTE_MS = 3000            # how long the "screen turning off" note shows first
ACT_GAP_MS = 2000                    # at most one activity animation every 2 s
OLD_BRIGHT = (1.0, 0.7, 0.45, 0.25)   # the four levels used before
MENU_FLAG = "/state/.burn_helper_menu"

prefs = {"theme": "hero", "bright": 0, "levels": 4, "seq": -1, "case_leds": False}
config.migrate()
State.load("burn_helper", prefs)
# theme ids used before the files were renamed
LEGACY_THEMES = {"zelda": "hero", "runningman": "gameshow", "forrest": "chocolates"}
prefs["theme"] = LEGACY_THEMES.get(prefs.get("theme"), prefs.get("theme"))
if prefs.get("theme") not in THEMES:
    prefs["theme"] = "hero"
if prefs.get("levels") not in (10, len(BRIGHT)):
    # saved with the old four levels: keep the same brightness on the new scale
    old = OLD_BRIGHT[prefs.get("bright", 0) % len(OLD_BRIGHT)]
    prefs["bright"] = min(range(OFF), key=lambda i: abs(BRIGHT[i] - old))
prefs["levels"] = len(BRIGHT)
if prefs["bright"] >= OFF:
    # never start with a dark screen: a badge that boots black looks dead
    prefs["bright"] = OFF - 1

st = S.Status()


def new_link():
    """The Wi-Fi link, from the networks saved right now (the last one that worked tried first)."""
    return net.Net(config.networks(), config.bridge(), relay=config.load_relay(),
                   last=config.last_network(), on_join=config.save_last_network,
                   paired=config.paired_bridge(), key=config.load_key())


link = new_link()
tether = usb.UsbLink()
themes = {}
view = 0        # 0 animation, then views.DESKTOP, views.DEBUG
page = 0        # the page shown in Debug mode
wait_sel = None # Desktop mode: which waiting session is shown in detail (None: the summary)
wait_since = None        # ticks_ms when a session started waiting
screen_off_at = None     # ticks_ms when the backlight goes off after the 0% note
lost_test = None         # the @LOST test over USB: ticks_ms the data is taken to have stopped at
pace_test = None         # the @PACE test over USB: a weekly pace shown instead of the bridge's
demo = 0            # 0 off, 1 demo with a DEMO tag, 2 the hidden 20-second video take
demo_t0 = 0         # ticks_ms when the demo started
DEMO_HOLD_MS = 2000      # hold UP alone
HIDDEN_HOLD_MS = 3000    # hold UP + DOWN together
PORTAL_HOLD_MS = 1800    # hold B alone
SHORT_MS = 700           # longer than this is a hold, not a press
down = {}                # button -> ticks when it went down
fired = False            # a hold fired; ignore releases until every button is up
wink_until = 0
last_act = 0            # ticks_ms when the last activity animation started
portal = None
portal_arm = False       # B is still down from the hold that opened setup; its release must not cancel
b_down_t = None
seen = {"usb": 0, "net": 0}
source = None   # "usb" or "net": where the current numbers came from
last_input = time.ticks_ms()
theme_cost = {}          # theme -> (heap bytes its sprites took, ms to build them), for the memory report
leds_lit = True          # LEDs may be lit (unknown at start): the first frame turns them off unless enabled
dimmed = False
frame_t = time.ticks_ms()
toast = None
toast_t = 0
perf = [0.0, 0.0]   # moving averages: draw ms, frame-to-frame ms
boot_ms = time.ticks_ms()
power.trim()
ctx = views.Ctx(st, link, tether)


def set_brightness(i):
    try:
        display.backlight(BRIGHT[i % len(BRIGHT)])
    except Exception:  # noqa: BLE001
        pass


set_brightness(prefs["bright"])


def show_toast(msg):
    global toast, toast_t
    toast = msg
    toast_t = time.ticks_ms()


def theme_obj(name):
    th = themes.get(name)
    if th is None:
        # building sprites takes a moment, so say so
        screen.pen = color.rgb(0, 0, 0)
        screen.clear()
        gfx.ctext("LOADING", 80, 44, (255, 255, 255), font.sins)
        gfx.ctext(LABELS[name], 80, 58, (217, 119, 87), font.sins)
        display.update()
        gc.collect()
        mem0, t0 = gc.mem_alloc(), time.ticks_ms()
        mod = __import__("theme_" + name)
        th = mod.Theme()
        th.build()
        th.ready = True
        themes[name] = th
        gc.collect()
        theme_cost[name] = (gc.mem_alloc() - mem0, time.ticks_diff(time.ticks_ms(), t0))
    return th


def switch(delta=0, name=None):
    global demo
    if name is None:
        i = THEMES.index(prefs["theme"])
        name = THEMES[(i + delta) % len(THEMES)]
    if demo and name != DEMO_THEME:
        demo = 0                     # the demo only exists for the hero theme
    prefs["theme"] = name
    State.save("burn_helper", prefs)
    show_toast(LABELS[name])


def save_prefs():
    State.save("burn_helper", prefs)


def apply_bridge():
    """Copy the freshest bridge data (USB tether or Wi-Fi) into the status model."""
    global source
    d = None
    for name, src in (("net", link), ("usb", tether)):
        if src.seq != seen[name] and src.data is not None:
            seen[name] = src.seq
            # prefer USB while it is fresh; Wi-Fi fills in when unplugged
            if name == "usb" or not tether.fresh():
                d = src.data
                source = "relay" if (name == "net" and link.via == "relay") else name
    if d is None:
        return
    r = d.get("relay")
    if source == "usb" and isinstance(r, dict) and r.get("url") and r.get("key"):
        # the bridge hands over its internet relay over the cable only; keep it for later
        r = {"url": str(r["url"]), "key": str(r["key"])}
        if r != link.relay:
            config.save_relay(r)
            link.set_relay(r)
            show_toast("INTERNET RELAY READY")
    k = d.get("key")
    if source == "usb" and isinstance(k, str) and k and k != link.key:
        # the bridge's key comes over the cable only, and opens its sealed answers on Wi-Fi
        config.save_key(k)
        link.key = k
        link.http_err = ""
        show_toast("BRIDGE KEY SAVED")
    bid = d.get("bridge")
    if source == "usb" and isinstance(bid, str) and bid and bid != link.paired:
        # the bridge on the other end of the cable is this badge's bridge: from now on its beacon
        # is the one to follow on Wi-Fi, whatever other bridges are on the network
        config.save_paired_bridge(bid)
        link.paired = bid
    st.update(d)
    tseq = d.get("theme_seq")
    if isinstance(tseq, int) and tseq != prefs.get("seq"):
        prefs["seq"] = tseq
        want = LEGACY_THEMES.get(d.get("theme"), d.get("theme"))   # an older bridge sends the old ids
        if want in THEMES and want != prefs["theme"]:
            switch(name=want)
        else:
            save_prefs()


# Two demos, both on the hero theme only, each starting from its first frame:
#   demo 1 (hold UP 2 s, DEMO tag): a 30-second ramp from asleep through every activity level
#     up to ULTRA, with sessions waiting for you now and then and every activity animation
#     along the way, on a 90-second usage window (the hearts refill when it resets), and the
#     weekly reset's whole ladder sped up inside the same 90 seconds (DEMO_WEEK).
#   demo 2 (hold UP + DOWN 3 s, no tag): a 20-second take for the launch video, timed to the
#     shot list in docs/video.md.
DEMO_THEME = "hero"
DEMO_CYCLE_MS = 30000
DEMO_AGENTS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 18, 40, 63, 88, 128)   # one count inside each tier
DEMO_WAITS = {3: 1, 7: 2, 12: 1}             # tier -> sessions waiting while it runs
DEMO_WAITING = ({"n": "api-server refactor", "s": 95, "d": "api-server", "w": "PERMISSION: BASH", "a": 7800},
                {"n": "docs-site-amber-42", "s": 12, "d": "docs-site", "w": "YOUR REPLY", "a": 1500, "i": "7f3a2c", "u": 0})
# (ms into the 30-second cycle, activity) for demo 1: one after another, each 1-2 s long
DEMO_ACTS = ((2000, "arrive"), (3900, "prompt"), (5600, "edit"), (7300, "read"), (9200, "shell"),
             (11100, "web"), (12800, "spawn"), (15100, "edit"), (16800, "fail"), (18100, "edit"),
             (19800, "shell"), (21700, "read"), (23400, "done"))
DEMO_USAGE_MS = 90000
DEMO_RESET_MS = 75000       # into the usage window: the 5-hour countdown runs out, hearts refill
# the weekly reset in demo 1, sped up inside its 90-second window: (from s, to s, seconds left at
# the start, at the end, how many times faster than real time it runs there)
DEMO_WEEK = ((0, 12, 3 * 86400 + 4 * 3600, 3 * 86400 + 4 * 3600, 1),     # a quiet week
             (12, 18, 5 * 3600 + 59 * 60, 5 * 3600 + 40 * 60, 190),      # under 6 hours
             (18, 24, 59 * 60, 50 * 60, 90),                              # under an hour
             (24, 44, 300, 62, 12),                                       # under 10 minutes
             (44, 56, 59, 11, 4),                                         # under a minute
             (56, 66, 10, 0, 1),                                          # under ten seconds
             (66, 70, 0, -4, 1),                                          # the reset itself
             (70, 90, 7 * 86400, 7 * 86400 - 20, 1))                      # a new week
VIDEO_MS = 20000
# (second it starts, level when no agents work, agents working, sessions waiting)
VIDEO_STEPS = ((0.0, S.SLEEP, 0, 0),     # asleep
               (3.0, S.IDLE, 0, 0),      # wakes up
               (4.5, S.WALK, 1, 0),      # one agent: walks
               (7.0, S.WALK, 5, 0),      # five: runs
               (8.5, S.WALK, 9, 0),      # nine: sprints
               (10.0, S.WALK, 9, 1),     # a session needs you: "HEY! LISTEN!"
               (12.4, S.WALK, 9, 0),     # you answered it (the new quest scroll below)
               (13.0, S.WALK, 40, 0),    # 26-50 band: sparks
               (15.0, S.WALK, 88, 0),    # 76-100 band: pulsing edge
               (16.0, S.WALK, 128, 0))   # over 100: hyperspace until the end
# (second it starts, activity) for demo 2
VIDEO_ACTS = ((3.0, "arrive"),           # steps out of a cave: a session starts
              (5.6, "edit"),             # sword combo: the agent edits a file
              (12.4, "prompt"),          # you answered: a new quest scroll
              (14.0, "done"))            # item get: QUEST COMPLETE!


def set_demo(kind):
    """Start demo 1 or 2 from its first frame, or stop (0). Demos run on the hero theme."""
    global demo, demo_t0
    demo = kind
    demo_t0 = time.ticks_ms()
    if demo and prefs["theme"] != DEMO_THEME:
        switch(name=DEMO_THEME)


def demo_week(ms):
    """(microseconds to the weekly reset, speed-up) at ms into the demo's 90-second window."""
    s = ms / 1000.0
    for a, b, l0, l1, rate in DEMO_WEEK:
        if s < b:
            return int((l0 + (l1 - l0) * (s - a) / (b - a)) * 1000000), rate
    return 7 * 86400 * 1000000, 1


def demo_status(t):
    k = time.ticks_diff(t, demo_t0)
    since = k
    act = None
    if demo == 2:
        k %= VIDEO_MS
        level, agents, waiting = S.SLEEP, 0, 0
        for start, lv, n, w in VIDEO_STEPS:
            if k >= start * 1000:
                level, agents, waiting = lv, n, w
        for start, key in VIDEO_ACTS:
            if k >= start * 1000:
                act, at = key, t - (k - int(start * 1000))
    else:
        win = since % DEMO_USAGE_MS
        k %= DEMO_CYCLE_MS
        for start, key in DEMO_ACTS:
            if k >= start:
                act, at = key, t - (k - start)
        if DEMO_RESET_MS <= win < DEMO_RESET_MS + 2500:
            act, at = "refill", t - (win - DEMO_RESET_MS)
        if k < 2000:
            agents, level, waiting = 0, S.SLEEP, 0
        elif k < 3500:
            agents, level, waiting = 0, S.IDLE, 0
        else:
            # tiers 1-14 for 1.6 s each, then ULTRA for the last 4 s
            tier = min((k - 3500) // 1600, 14) + 1
            agents, level, waiting = DEMO_AGENTS[tier - 1], S.WALK, DEMO_WAITS.get(tier, 0)
    if view == views.DESKTOP:
        waiting = 2                              # so Desktop mode always has sessions to show
    st.level = level
    st.busy, st.subagents = agents, 0
    st.set_agents(agents)
    st.waiting = waiting
    st.waiting_list = list(DEMO_WAITING[:waiting])
    st.idle = 2
    st.sessions = agents + waiting + 2
    st.tpm = min(60, 4 * st.tier)
    st.online = True
    st.net = ""
    st.week = 0.6
    st.used7 = 40
    st.pace = None                           # made-up usage: no real week's pace with it
    if demo == 1:
        st.left7, st.wk_rate = demo_week(time.ticks_diff(t, demo_t0) % DEMO_USAGE_MS)
    else:
        st.left7, st.wk_rate = (3 * 86400 + 4 * 3600) * 1000000, 1
    if demo == 2:
        # the take: hearts drain from full to low, and the 5-hour countdown runs out at 20 s
        st.tools = 200 + k // 40
        st.left5 = (VIDEO_MS - k) * 1000 - time.ticks_us() % 1000
        st.hearts = max(3, 20 - 17 * k // 19000)
    else:
        # a 90-second usage window: hearts drain for 75 s while the countdown runs
        # down through minutes, milliseconds and microseconds, then it resets
        st.tools = 1234
        into = (time.ticks_diff(t, demo_t0) % 90000) * 1000 + time.ticks_us() % 1000
        st.left5 = 75 * 1000000 - into
        st.hearts = 20 if st.left5 <= 0 else max(0, 20 - into // 3750000)
    st.used5 = (20 - st.hearts) * 5
    if act is not None and at != st.act_seq:
        st.act, st.act_t, st.act_seq = act, at, at      # its start time doubles as its number


WAIT_FLASH_MS = 1500     # a session needs you: all four LEDs flash for this long,
WAIT_FLASH_PERIOD = 250  # (on/off every this many ms),
WAIT_LED_STEP_MS = 180   # then one light runs round the four until you answer
wait_led_t0 = None       # ticks_ms when the waiting alert began


def week_lights(t):
    """The case LEDs for the weekly reset's last ten minutes, in a rhythm of their own (a slow breathe,
    faster each stage, a pulse on every second in the last ten, and all four flashing at the reset).
    Returns False when it is not that time."""
    stage = S.week_stage(st)
    if stage in (None, "six", "hour"):
        return False
    if stage == "zero":
        k = int((S.week_zero_progress(st) or 0) * S.WEEK_ZERO_MS)
        badge.caselights(0.8 if (k // 200) % 2 == 0 else 0.1)
        return True
    if stage == "ten":
        v = 0.06 + 0.1 * (1 + math.sin(t / 700.0))                  # a slow breathe
    elif stage == "minute":
        v = 0.1 + 0.2 * (1 + math.sin(t / 250.0))                   # quicker
    else:
        v = 0.7 if ((st.left7 // 1000) % 1000) > 850 else 0.08       # a flash as every second ticks over
    badge.caselights(v)
    return True


def waiting_lights(t):
    """The LED alert for a session waiting for you: a flash, then a light running round. It works
    even with the other case lights switched off (they are only for activity)."""
    global wait_led_t0
    if wait_led_t0 is None:
        wait_led_t0 = t
    k = time.ticks_diff(t, wait_led_t0)
    if k < WAIT_FLASH_MS:
        badge.caselights(0.8 if (k // WAIT_FLASH_PERIOD) % 2 == 0 else 0.0)
    else:
        i = (k // WAIT_LED_STEP_MS) % 4
        badge.caselights(*[0.6 if j == i else 0.0 for j in range(4)])


def lights(t):
    """The four case LEDs. In both demos they are always on (pulsing with activity, and the waiting
    alert). Otherwise the activity pulsing is off unless switched on (hold DOWN 2 s), and only a
    waiting session lights them (a flash, then a running light)."""
    global leds_lit, wait_led_t0
    if time.ticks_diff(wink_until, t) > 0:
        badge.caselights(0.8)
        leds_lit = True
        return
    if st.waiting and st.online:
        leds_lit = True
        waiting_lights(t)
        return
    wait_led_t0 = None                   # the next waiting session starts with the flash again
    if st.online and week_lights(t):
        leds_lit = True
        return
    if not (prefs.get("case_leds", False) or demo):
        if leds_lit:                     # just switched off: do not leave them glowing
            badge.caselights(0)
            leds_lit = False
        return
    leds_lit = True
    lv = st.level if st.online else S.SLEEP
    if lv == S.SLEEP:
        badge.caselights(0)
    elif lv == S.IDLE:
        badge.caselights(0.04)
    elif lv == S.WALK:
        badge.caselights(0.08 + 0.08 * (1 + math.sin(t / 600.0)))
    elif lv == S.RUN:
        badge.caselights(0.15 + 0.15 * (1 + math.sin(t / 250.0)))
    else:
        k = (t // 120) % 4
        badge.caselights(*[0.5 if i == k else 0.05 for i in range(4)])




def is_up(b, t):
    """True once a button is physically released (they read 0 while pressed)."""
    if badge.released(b):
        return True
    try:
        return b.value() == 1 and time.ticks_diff(t, down[b]) > 100
    except Exception:  # noqa: BLE001
        return False


def wifi_trouble():
    return not tether.fresh() and link.state != "up"


def step_waiting(d):
    """Desktop mode's A/C: summary -> each waiting session in turn -> summary."""
    global wait_sel
    n = len(st.waiting_list)
    i = -1 if wait_sel is None else wait_sel
    i = (i + 1 + d) % (n + 1) - 1          # -1 is the summary
    wait_sel = None if i < 0 else i


def wake_screen(b):
    """The screen is off (0%): any button wakes it. DOWN goes round to full brightness, as it always
    did; the others come on at the dimmest lit level, which is gentle at night."""
    global screen_off_at
    prefs["bright"] = 0 if b == BUTTON_DOWN else OFF - 1
    screen_off_at = None
    save_prefs()
    set_brightness(prefs["bright"])
    show_toast("SCREEN ON")
    power.note("screen woken by a button press")


def short_press(b):
    global view, page, wait_sel, screen_off_at
    if screen_dark():
        wake_screen(b)
        return
    if not (b == BUTTON_UP and view == views.DEBUG and page == views.WIFI_PAGE):
        link.pick_cancel()                  # any other press, or leaving the page, drops a pick
    if b in (BUTTON_A, BUTTON_C):
        d = 1 if b == BUTTON_C else -1
        if view == views.DEBUG:
            page = (page + d) % len(views.PAGES)
        elif view == views.DESKTOP:
            step_waiting(d)
        else:
            switch(d)                   # themes change only on the animation
    elif b == BUTTON_B:
        view = (view + 1) % 3
        wait_sel = None
        if view == views.DEBUG and wifi_trouble():
            page = views.WIFI_PAGE      # the badge's "PRESS B x2" hint leads straight here
    elif b == BUTTON_UP and view == views.DEBUG and page == views.WIFI_PAGE:
        # step through the saved networks; the badge connects to the one picked a moment later
        link.pick_next()
    elif b == BUTTON_DOWN:
        prefs["bright"] = (prefs["bright"] + 1) % len(BRIGHT)
        save_prefs()
        if prefs["bright"] == OFF:
            # keep the screen lit for a moment to say what is happening, then turn it off
            screen_off_at = time.ticks_add(time.ticks_ms(), SCREEN_OFF_NOTE_MS)
            power.note("screen going off (0%)")
        else:
            screen_off_at = None
            set_brightness(prefs["bright"])
            show_toast("BRIGHTNESS %d%%" % int(BRIGHT[prefs["bright"]] * 100 + 0.5))


def handle_buttons(t):
    """Short presses act on release; holds act once while held."""
    global view, demo, portal, portal_arm, last_input, dimmed, fired, wink_until, link
    if badge.pressed() or badge.held():
        last_input = t
        if dimmed:
            dimmed = False
            set_brightness(prefs["bright"])
    for b in (BUTTON_A, BUTTON_B, BUTTON_C, BUTTON_UP, BUTTON_DOWN):
        if badge.pressed(b) and b not in down:
            down[b] = t
            if screen_dark():
                # with nothing on screen a press is not a quick tap: wake on the press itself, not on its
                # release (a press held for a moment used to count as a hold and did nothing)
                down.clear()
                wake_screen(b)
                return
    if portal is not None:
        if portal_arm:
            # setup stays open after the hold: wait for that press to end, then a new B press cancels
            if BUTTON_B not in down or is_up(BUTTON_B, t):
                portal_arm = False
                down.clear()
        elif portal.phase == "serve" and BUTTON_B in down and is_up(BUTTON_B, t):
            down.clear()
            portal.close()
            portal = None
            # setup saves a network as soon as you submit it, even when its test join fails,
            # so start again from the saved list rather than the one the badge booted with
            link = new_link()
        return

    def held(b):
        return time.ticks_diff(t, down[b]) if b in down else -1

    if not fired:
        if held(BUTTON_UP) >= HIDDEN_HOLD_MS and held(BUTTON_DOWN) >= HIDDEN_HOLD_MS:
            # undocumented: demo with no on-screen tag, for videos and talks
            fired = True
            set_demo(0 if demo else 2)
            wink_until = time.ticks_add(t, 350)
        elif held(BUTTON_DOWN) >= DEMO_HOLD_MS and BUTTON_UP not in down and len(down) == 1:
            fired = True
            prefs["case_leds"] = not prefs.get("case_leds", False)
            save_prefs()
            show_toast("CASE LIGHTS ON" if prefs["case_leds"] else "CASE LIGHTS OFF")
        elif held(BUTTON_UP) >= DEMO_HOLD_MS and BUTTON_DOWN not in down:
            fired = True
            set_demo(0 if demo else 1)
            show_toast("DEMO ON" if demo else "DEMO OFF")
        elif held(BUTTON_B) >= PORTAL_HOLD_MS and len(down) == 1:
            fired = True
            view = 0
            start_portal()
            portal_arm = portal is not None
            return
    for b in list(down):
        if is_up(b, t):
            dur = time.ticks_diff(t, down.pop(b))
            if not fired and dur <= SHORT_MS:
                short_press(b)
    if not down:
        fired = False


def start_portal():
    global portal
    if prefs["bright"] == OFF:
        # phone setup needs the screen: come back on at the dimmest lit level
        prefs["bright"] = OFF - 1
        set_brightness(prefs["bright"])
    link.stop()
    try:
        import portal as P
        portal = P.Portal(link.results())
    except Exception as e:  # noqa: BLE001
        show_toast("SETUP FAILED")
        link.err = repr(e)[:40]
        portal = None


def finish_portal():
    """The phone setup tried the new network. Success: back to the main screen on it.
    Failure: back to setup with a note, so the password can be fixed."""
    global portal, portal_arm, link
    ok = portal.outcome == "ok"
    ssid = portal.new_ssid
    portal.close()
    down.clear()
    if ok:
        portal = None
        link = new_link()
        show_toast("WI-FI " + ssid[:14].upper())
    else:
        link.stop()
        try:
            import portal as P
            portal = P.Portal(link.results(), notice="LAST TRY FAILED: CHECK PW")
            portal_arm = False
        except Exception:  # noqa: BLE001
            portal = None


def power_save(t):
    global dimmed
    # asleep, or the connection-lost page left up (a bridge asleep for the night, say)
    quiet = st.level == S.SLEEP or S.lost_stage(st, t) == "lost"
    if not dimmed and BRIGHT[prefs["bright"]] > 0.12 and quiet \
            and time.ticks_diff(t, last_input) > 10 * 60 * 1000:
        dimmed = True
        try:
            display.backlight(0.12)
        except Exception:  # noqa: BLE001
            pass
    if dimmed and not quiet:
        dimmed = False
        set_brightness(prefs["bright"])


def screen_dark():
    return prefs["bright"] == OFF and screen_off_at is None


def draw_off_note(left_ms):
    gfx.box(8, 32, 144, 52, (0, 0, 0))
    gfx.box(8, 32, 144, 1, (217, 119, 87))
    gfx.ctext("SCREEN OFF IN %d" % ((left_ms + 999) // 1000), 80, 35, (255, 255, 255), font.sins)
    gfx.ctext("THE BADGE STAYS ON", 80, 50, (110, 220, 120), font.sins)
    gfx.ctext("DOWN: SCREEN BACK ON", 80, 65, (150, 150, 160), font.sins)


def pace(t):
    """Cap the frame rate: smooth when busy, frugal when asleep."""
    global frame_t
    target = 90 if ((st.level == S.SLEEP and not st.waiting) or S.lost_stage(st, t) == "lost") else 40
    if view or screen_dark():
        target = 100       # static screens or a dark screen: nothing animates, 10 fps still catches a quick tap
    spent = time.ticks_diff(time.ticks_ms(), frame_t)
    try:
        if spent < target:
            time.sleep_ms(target - spent)
    except KeyboardInterrupt:
        # Ctrl-C over USB (tools/deploy.py --shot): keep the finished frame
        try:
            import screenshot
            screenshot.save("/shot.png")
        except Exception:  # noqa: BLE001
            pass
        raise
    now = time.ticks_ms()
    perf[1] = perf[1] * 0.9 + time.ticks_diff(now, frame_t) * 0.1
    frame_t = now


def draw_frame(t):
    global wait_sel, last_act
    if view == 0:
        th = theme_obj(prefs["theme"])
        if not demo:
            # what the agents just did, played one at a time (the demos script their own)
            free = th.acting(t) is None and time.ticks_diff(t, last_act) >= ACT_GAP_MS
            if st.next_act(t, free):
                last_act = t
        th.draw(st, t)
        if demo == 1:
            gfx.text("DEMO", 136, 96, (255, 255, 255), font.sins, shadow=(0, 0, 0))
    else:
        # Desktop and Debug mode are opaque: the animation is paused behind them (no theme
        # drawing, and pace() slows the loop). They are redrawn every frame because the
        # firmware does not keep the previous one.
        if wait_sel is not None and wait_sel >= len(st.waiting_list):
            wait_sel = len(st.waiting_list) - 1 if st.waiting_list else None   # one was answered
        ctx.link, ctx.source, ctx.demo, ctx.wait_since = link, source, demo, wait_since
        ctx.wait_sel = wait_sel
        views.draw(view, page, ctx, t)
    if toast is not None and time.ticks_diff(t, toast_t) < 1500:
        w = gfx.width(toast, font.sins) + 8
        gfx.box(80 - w // 2, 48, w, 13, (0, 0, 0))
        gfx.box(80 - w // 2, 48, w, 1, (217, 119, 87))
        gfx.ctext(toast, 80, 48, (255, 255, 255), font.sins)
    bw = power.warning()
    if views.battery_banner(bw, t) and screen_off_at is None:
        views.draw_battery_warning(bw)
    if screen_off_at is not None:
        draw_off_note(time.ticks_diff(screen_off_at, t))


test_state = None        # a state shown for testing over USB ("@STATE est"), or None
BAT_FAKE = {"batlow": (False, False, 3.40, 18), "batcrit": (False, False, 3.28, 7)}   # (usb, charging, volts, %)


def apply_test_state():
    """Show a state that is hard to catch for real, over what the bridge says (USB "@STATE name").
    est: a new 5-hour window nobody has reported (full hearts, a ~ countdown); nobridge: no data;
    batlow, batcrit: the battery warning (18% and 7%, unplugged), whatever the battery really is;
    week: "week" mode (a plan with only a weekly limit), 6 hearts now and 3 likely left at the reset."""
    if test_state == "week":
        st.mode, st.hearts, st.hearts_end, st.used7, st.used5 = "week", 12, 6, 40, None
        st.left7 = (2 * 86400 + 5 * 3600) * 1000000 - (time.ticks_ms() % 1000) * 1000
        st.week = 0.6
        if st.pending == "refill":
            st.pending = None                # the bridge's hearts after the test's own: no refill
    elif test_state == "est":
        st.used5, st.est5, st.hearts = None, True, 20
        st.left5 = (4 * 3600 + 49 * 60) * 1000000 - (time.ticks_ms() % 1000) * 1000
        st.usage_state = "est"
    elif test_state == "nobridge":
        st.online = False
        st.seen_ms = None                    # as before the first data; @LOST shows the lost look
        st.net = "SEARCHING FOR BRIDGE..."


def update():
    global wait_since, screen_off_at
    t = time.ticks_ms()
    t_start = t
    handle_buttons(t)
    if portal is not None:
        portal.tick()
        if portal.phase == "done":
            finish_portal()
            return
        portal.draw(t)
        return
    link.tick()
    tether.tick()
    apply_bridge()
    st.online = link.fresh() or tether.fresh()
    st.net = "" if tether.fresh() else link.label()
    st.trouble = link.trouble()
    power.fake = BAT_FAKE.get(test_state)     # the @STATE batlow / batcrit tests; None otherwise
    if lost_test is not None:
        st.online = False                     # the @LOST test: as if the data had stopped then
        st.seen_ms = lost_test
    if pace_test is not None:
        st.pace = pace_test                   # the @PACE test: this pace, whatever the bridge says
    if demo:
        demo_status(t)
    else:
        S.track_lost(st, t)                   # while the data is lost, nothing is shown working
        st.tick()
        if test_state:
            apply_test_state()
    if st.waiting > 0:
        if wait_since is None:
            wait_since = t
    else:
        wait_since = None
    if screen_off_at is not None and time.ticks_diff(screen_off_at, t) <= 0:
        screen_off_at = None
        set_brightness(prefs["bright"])       # the 0% level: backlight off
    if not screen_dark():
        draw_frame(t)
    lights(t)
    power_save(t)
    power.tick(boot_ms)
    perf[0] = perf[0] * 0.9 + time.ticks_diff(time.ticks_ms(), t_start) * 0.1
    if tether.demo_req is not None:
        set_demo(tether.demo_req % 3)
        tether.demo_req = None
    if tether.test_req is not None:
        globals()["test_state"] = None if tether.test_req in ("normal", "off", "") else tether.test_req
        tether.test_req = None
    if tether.view_req is not None:
        globals()["view"] = tether.view_req % 3
        tether.view_req = None
    if tether.key_req is not None:
        key = {"A": BUTTON_A, "B": BUTTON_B, "C": BUTTON_C, "UP": BUTTON_UP, "DOWN": BUTTON_DOWN}.get(tether.key_req)
        tether.key_req = None
        if key is not None:
            short_press(key)
    if tether.pace_req is not None:
        globals()["pace_test"] = None if tether.pace_req == "off" else S.pace_of(tether.pace_req)
        tether.pace_req = None
    if tether.lost_req is not None:
        globals()["lost_test"] = None if tether.lost_req < 0 else time.ticks_add(t, -tether.lost_req * 1000)
        tether.lost_req = None
    if tether.relay_req is not None:
        link.force_relay = bool(tether.relay_req)
        tether.relay_req = None
    if tether.page_req is not None:
        globals()["page"] = tether.page_req % len(views.PAGES)
        tether.page_req = None
    if tether.netlog_req:
        tether.netlog_req = False
        try:
            gc.collect()
            mem = ["memory: heap used %d KB, free %d KB" % (gc.mem_alloc() // 1024, gc.mem_free() // 1024)]
            mem += ["  theme %s: %d KB of sprites, built in %d ms" % (n, c[0] // 1024, c[1]) for n, c in theme_cost.items()]
            try:
                with open(CRASH_LOG) as f:
                    crash_tail = ["-- crashes --"] + f.read()[-1500:].split("\n")
            except Exception:  # noqa: BLE001
                crash_tail = []
            usb.send_lines("NETLOG", link.dump() + mem + ["-- power --"] + power.recent() + crash_tail
                           + ["-- log --"] + link.log)
        except Exception as e:  # noqa: BLE001
            print("@NETLOG-ERR", e)
    if tether.shot_req:
        tether.shot_req = False
        try:
            usb.send_screenshot("draw_ms=%.1f frame_ms=%.1f theme=%s level=%d src=%s act=%s" % (
                perf[0], perf[1], prefs["theme"], st.level, source, st.act))
        except Exception as e:  # noqa: BLE001
            print("@SHOTERR", e)
    pace(t)
    return


def on_exit():
    # HOME was pressed: next boot shows the stock menu instead of this app.
    try:
        badge.caselights(0)
    except Exception:  # noqa: BLE001
        pass
    try:
        with open(MENU_FLAG, "w") as f:
            f.write("1")
    except Exception:  # noqa: BLE001
        pass


CRASH_LOG = "/state/burn_helper_crash.log"
crashes = []             # ticks_ms of recent crashes in update()


def crash(e):
    """update() raised. Do not let the firmware's error screen take over (with the backlight off it
    looks like a dead badge): write it down, make sure the screen is on, carry on, and restart the
    badge if it keeps happening."""
    now = time.ticks_ms()
    crashes.append(now)
    while crashes and time.ticks_diff(now, crashes[0]) > 60000:
        crashes.pop(0)
    try:
        import io
        import sys
        buf = io.StringIO()
        sys.print_exception(e, buf)
        import os
        try:
            big = os.stat(CRASH_LOG)[6] > 8192
        except OSError:
            big = False
        with open(CRASH_LOG, "w" if big else "a") as f:
            f.write("---- %d s: %s\n%s" % (time.ticks_diff(now, boot_ms) // 1000, repr(e)[:120], buf.getvalue()[-900:]))
    except Exception:  # noqa: BLE001
        pass
    global screen_off_at
    if prefs["bright"] == OFF:
        prefs["bright"] = OFF - 1
        screen_off_at = None
    set_brightness(prefs["bright"])
    if len(crashes) >= 10:
        try:
            import machine
            machine.reset()
        except Exception:  # noqa: BLE001
            pass


def safe_update():
    try:
        return update()
    except KeyboardInterrupt:
        raise
    except Exception as e:  # noqa: BLE001
        crash(e)
        try:
            time.sleep_ms(100)
        except Exception:  # noqa: BLE001
            pass


run(safe_update)
