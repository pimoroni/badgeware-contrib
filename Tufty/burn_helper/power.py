# Battery and USB power: an estimate of the battery's charge for the screens, and a small log so
# the battery can be checked after the badge has run unplugged (python3 tools/netdebug.py shows it).
#
# The firmware's badge.battery_level() turns the battery voltage straight into a percentage, and
# that goes wrong two ways. Its voltage is corrected against a "1.1 V" reference that really reads
# 1.164 V, so it is about 5% low, and further off as the 3.3 V supply sags on a nearly empty
# battery (it showed 0% for ten minutes while the badge kept running). And while USB charges the
# battery the voltage reads well above its real charge, so the level leapt from 1% to 50% in a
# minute. So the badge keeps its own estimate:
#   * the voltage is measured against the reference's real value, which also follows the sag,
#   * mapped through a discharge curve measured on this badge, at its own load,
#   * smoothed, so a short dip under load (Wi-Fi sending) doesn't move it,
#   * on battery it only goes down (up only slowly, to correct itself after charging),
#   * charging, it rises no faster than the battery can take charge, 100% when the charger stops,
#   * and it is kept across app restarts.
# From how fast the estimate falls on battery it also works out the time left unplugged, and it
# learns the badge's usual drain from every long enough run on battery (kept with the estimate),
# so the time left is sound from the first minutes of the next run.

import time

LOG_FILE = "/state/burn_helper_power.log"
SOC_FILE = "/state/burn_helper_soc.json"
LOG_MAX = 48 * 1024         # about 13 hours of one line a minute: a whole run on battery
CACHE_MS = 2000
LOG_ON_BATTERY_MS = 60 * 1000
LOG_ON_USB_MS = 5 * 60 * 1000

REF_VOLTS = 1.164            # what the "1.1 V" rail really is on this badge (logged while healthy)
# true battery volts under the badge's own load -> percent left, measured from a full discharge
# (the bottom from timed log lines, the top from a fresh unplug at 4.13 V)
CURVE = ((3.07, 0.0), (3.27, 2.5), (3.37, 6.0), (3.39, 9.0), (3.456, 15.0), (3.52, 19.0), (3.58, 25.0),
         (3.64, 33.0), (3.69, 42.0), (3.74, 52.0), (3.80, 62.0), (3.87, 72.0), (3.95, 82.0),
         (4.05, 92.0), (4.13, 100.0))
CHARGE_OFFSET = 0.15         # charging lifts the battery's voltage about this much above its real charge
CHARGE_PCT_PER_MIN = 1.0     # at most this fast while charging (about 100 minutes from empty to full)
RISE_PCT_PER_MIN = 0.5       # on battery the estimate only creeps up, to correct itself after charging
SMOOTH = 0.08                # how much each 2-second reading moves the smoothed voltage
KEEP_SOC_MS = 10 * 60 * 1000 # a saved estimate older than this is not trusted after a restart
DEFAULT_RATE = 11.0          # %/hour until it has learnt its own (one full run took about 9 hours)
LEARN_MIN_MINUTES = 30       # a run on battery teaches the drain only if it lasted this long
LEARN_MIN_DROP = 5.0         # and used this much

LOW_PCT = 20                 # on battery at or under this: a banner now and then
CRITICAL_PCT = 10            # and at or under this: a banner that stays

fake = None                  # a reading shown for testing over USB ("@STATE batlow"), or None
_cache = [None, None]        # reading, ticks_ms it was taken
_log = [None, None]          # ticks_ms of the last log line, usb state at that line
_est = {"v": None, "soc": None, "t": None, "saved": None,
        "rate": None, "runs": 0,           # learnt drain in %/hour, and from how many runs
        "run": None,                       # this run on battery: (time.time() it began, estimate then)
        "run_t": None}                     # ticks_ms it began, when it began since the app started


def soc_from_volts(v):
    """Percent left for a true battery voltage on battery, from CURVE."""
    if v <= CURVE[0][0]:
        return 0.0
    for (v0, p0), (v1, p1) in zip(CURVE, CURVE[1:]):
        if v <= v1:
            return p0 + (p1 - p0) * (v - v0) / (v1 - v0)
    return 100.0


def estimate(soc, v, usb, charging, minutes):
    """The next estimate from the last one (None at first), the smoothed true voltage, the power
    state and the minutes since the last estimate."""
    if usb and not charging:
        # on the cable and not charging: the charger has finished (or there is no battery)
        return 100.0 if v >= 3.9 else soc_from_volts(v)
    target = soc_from_volts(v - CHARGE_OFFSET) if charging else soc_from_volts(v)
    if soc is None:
        return target
    if charging:
        return max(soc, min(target, soc + CHARGE_PCT_PER_MIN * minutes))
    if target < soc:
        return target
    return min(target, soc + RISE_PCT_PER_MIN * minutes)


def true_volts():
    """The battery voltage measured against the 1.1 V rail's real value, or None."""
    naive, ref = _raw()
    if not naive or not ref:
        return None
    return naive * REF_VOLTS / ref


def _load():
    try:
        import json
        with open(SOC_FILE) as f:
            return json.loads(f.read())
    except Exception:  # noqa: BLE001
        return {}


def _save():
    e = _est
    try:
        import json
        with open(SOC_FILE, "w") as f:
            f.write(json.dumps({"soc": round(e["soc"], 1), "at": time.time(), "rate": e["rate"],
                                "runs": e["runs"], "run": e["run"]}))
    except Exception:  # noqa: BLE001
        pass


def learn(rate, runs, minutes, drop):
    """The drain to remember after a run on battery of `minutes` that used `drop` percent:
    (rate, runs). Short or tiny runs teach nothing; each new run counts for 30%."""
    if minutes < LEARN_MIN_MINUTES or minutes > 24 * 60 or drop < LEARN_MIN_DROP:
        return rate, runs
    seen = drop / (minutes / 60.0)
    if not 1.0 <= seen <= 100.0:
        return rate, runs                  # not a believable drain: a clock jump or a bad reading
    return (seen if rate is None else 0.7 * rate + 0.3 * seen), runs + 1


def minutes_left(soc, rate, runs, run_minutes, run_drop):  # noqa: ARG001
    """Minutes until empty at the drain seen in this run, leaning on the learnt (or default) drain
    while the run is still short."""
    base = rate if rate else DEFAULT_RATE
    if run_minutes >= 20 and run_drop >= 3:
        w = min(1.0, run_minutes / 120.0)
        base = w * (run_drop / (run_minutes / 60.0)) + (1 - w) * base
    return max(0, int(soc / max(base, 1.0) * 60))


def read():
    """(usb, charging, volts, percent), or None if the firmware cannot tell. Cached for 2 s."""
    if fake is not None:
        return fake
    now = time.ticks_ms()
    if _cache[1] is not None and time.ticks_diff(now, _cache[1]) < CACHE_MS:
        return _cache[0]
    try:
        usb, charging = bool(badge.usb_connected()), bool(badge.is_charging())
        v = true_volts()
        if v is None:
            v = badge.battery_voltage()
    except Exception:  # noqa: BLE001
        _cache[0], _cache[1] = None, now
        return None
    e = _est
    e["v"] = v if e["v"] is None else e["v"] + SMOOTH * (v - e["v"])
    if e["t"] is None:
        d = _load()
        e["rate"], e["runs"] = d.get("rate"), int(d.get("runs") or 0)
        at = d.get("at")
        if d.get("soc") is not None and at is not None and 0 <= time.time() - at < KEEP_SOC_MS / 1000:
            e["soc"] = float(d["soc"])       # carry on from before the restart
            e["run"] = d.get("run")
    minutes = 0.0 if e["t"] is None else time.ticks_diff(now, e["t"]) / 60000.0
    e["soc"] = estimate(e["soc"], e["v"], usb, charging, minutes)
    e["t"] = now
    if usb and e["run"]:
        # plugged in after a run on battery: learn the drain from it
        e["rate"], e["runs"] = learn(e["rate"], e["runs"], run_minutes(now), e["run"][1] - e["soc"])
        e["run"] = e["run_t"] = None
        _save()
    elif not usb and not e["run"]:
        e["run"], e["run_t"] = (time.time(), e["soc"]), now
    if e["saved"] is None or time.ticks_diff(now, e["saved"]) > 60000:
        _save()
        e["saved"] = now
    r = (usb, charging, e["v"], int(e["soc"] + 0.5))
    _cache[0], _cache[1] = r, now
    return r


def run_minutes(now=None):
    """Minutes of this run on battery: by the badge's own timer, or by the clock across a restart
    (not trusted if the clock jumped)."""
    e = _est
    if not e["run"]:
        return 0.0
    if e["run_t"] is not None:
        return time.ticks_diff(now if now is not None else time.ticks_ms(), e["run_t"]) / 60000.0
    m = (time.time() - e["run"][0]) / 60.0
    return m if 0 <= m <= 24 * 60 else 0.0


def time_left():
    """(minutes left on battery, learnt from at least one run?) or None on USB or when unknown."""
    r = read()
    e = _est
    if r is None or r[0] or not e["run"]:
        return None
    return minutes_left(e["soc"], e["rate"], e["runs"], run_minutes(), e["run"][1] - e["soc"]), e["runs"] > 0


def left_text(minutes):
    """"7H20M", "45M"."""
    if minutes >= 60:
        return "%dH%02dM" % (minutes // 60, minutes % 60)
    return "%dM" % minutes


def warning(r=None, left=None):
    """None, or (level, first line, second line) when it is running on battery and low.
    Level 1 is low (LOW_PCT), level 2 critical (CRITICAL_PCT). r and left default to the live
    reading and time_left(); the time left is only quoted once the estimate has a run to go on."""
    if r is None:
        r = read()
        left = time_left()
    if r is None or r[0] or r[3] > LOW_PCT:
        return None
    pct = r[3]
    when = "~" + left_text(left[0]) + " LEFT" if left else None
    if pct <= CRITICAL_PCT:
        return 2, "BATTERY %d%%: PLUG IN NOW" % pct, when or "IT WILL TURN OFF SOON"
    return 1, "LOW BATTERY %d%%" % pct, ("PLUG IN: " + when) if when else "PLUG IN SOON"


def text(short=False):
    """What the screens show: "41% 3.62V" on battery, "64% CHARGING" or "USB" on the cable."""
    r = read()
    if r is None:
        return "?"
    usb, charging, volts, pct = r
    if usb and charging:
        return "%d%% CHG" % pct if short else "%d%% CHARGING" % pct
    if usb:
        # not charging on USB: the battery is full, or there is none
        if short:
            return "USB %d%%" % pct if volts >= 3.9 else "USB"
        return "USB, FULL" if volts >= 3.9 else "USB POWER"
    left = time_left()
    if short:
        # Desktop mode shows the time left only once it is learnt from a real run on battery
        return "%d%% %s" % (pct, left_text(left[0])) if left and left[1] else "%d%%" % pct
    return "%d%% %.2fV%s" % (pct, volts, (" ~" + left_text(left[0])) if left else "")


def _raw():
    """The battery voltage reckoned against a 3.3 V supply, and what the 1.1 V rail reads that way."""
    try:
        import machine
        cf = 3.3 / 65536
        vb = machine.ADC(machine.Pin.board.VBAT_SENSE)
        vr = machine.ADC(machine.Pin.board.SENSE_1V1)
        b = r = 0
        for _ in range(10):
            b += vb.read_u16()
            r += vr.read_u16()
        return b / 10 * cf * 2, r / 10 * cf
    except Exception:  # noqa: BLE001
        return 0.0, 0.0


def tick(boot_ms):
    """Log a reading every minute on battery, every 5 minutes on USB, and at every plug/unplug."""
    now = time.ticks_ms()
    r = read()
    if r is None:
        return
    usb = r[0]
    every = LOG_ON_USB_MS if usb else LOG_ON_BATTERY_MS
    if _log[0] is not None and _log[1] == usb and time.ticks_diff(now, _log[0]) < every:
        return
    _log[0], _log[1] = now, usb
    naive, vref = _raw()
    try:
        fw = "%.3f %d%%" % (badge.battery_voltage(), int(badge.battery_level()))
    except Exception:  # noqa: BLE001
        fw = "?"
    # compact, so a whole run on battery fits: seconds since start, BAT / USB / CHG (charging),
    # true volts, our estimate, then the raw readings and the firmware's own figures
    line = "%ds %s v=%.3f soc=%d raw=%.3f rail=%.3f fw=%s" % (
        time.ticks_diff(now, boot_ms) // 1000, "CHG" if r[1] else ("USB" if usb else "BAT"),
        r[2], r[3], naive, vref, fw.replace(" ", "/"))
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:  # noqa: BLE001
        pass


def note(msg):
    """A line in the power log that is not a reading (the screen going off or being woken)."""
    try:
        with open(LOG_FILE, "a") as f:
            f.write("%d %s\n" % (time.ticks_ms() // 1000, msg))
    except Exception:  # noqa: BLE001
        pass


def trim():
    """Keep the log small; call once at start."""
    try:
        import os
        if os.stat(LOG_FILE)[6] > LOG_MAX:
            with open(LOG_FILE) as f:
                keep = f.read()[-LOG_MAX * 3 // 4:]
            with open(LOG_FILE, "w") as f:
                f.write(keep)
        with open(LOG_FILE, "a") as f:
            f.write("---- app start ----\n")
    except Exception:  # noqa: BLE001
        pass


def recent(n=8):
    try:
        with open(LOG_FILE) as f:
            return [ln.rstrip("\n") for ln in f.read().split("\n")[-n - 1:] if ln]
    except Exception:  # noqa: BLE001
        return []
