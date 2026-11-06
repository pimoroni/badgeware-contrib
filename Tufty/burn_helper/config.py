# Where the badge gets its Wi-Fi networks and (optionally) a fixed bridge address.
#
#   /system/secrets.py            WIFI_SSID / WIFI_PASSWORD (stock firmware file),
#                                 optional WIFI_EXTRA = [("ssid", "pass"), ...]
#                                 optional BRIDGE = "192.168.1.20:8787"
#   /state/burn_helper_net.json   networks and bridge added from a phone via the
#                                 setup portal (hold B). Tried first.

import json

NET_FILE = "/state/burn_helper_net.json"


def _secrets():
    try:
        import secrets
        return secrets
    except Exception:  # noqa: BLE001
        return None


# The app was called Hearts Left, and claude_buddy before that; keep what an earlier
# install saved (phone-added Wi-Fi, theme and brightness, the logs).
OLD_NAMES = (
    ("/state/hearts_left_net.json", NET_FILE),
    ("/state/hearts_left.json", "/state/burn_helper.json"),
    ("/state/hearts_left_net.log", "/state/burn_helper_net.log"),
    ("/state/hearts_left_power.log", "/state/burn_helper_power.log"),
    ("/state/claude_buddy_net.json", NET_FILE),
    ("/state/claude_buddy.json", "/state/burn_helper.json"),
    ("/state/claude_buddy_net.log", "/state/burn_helper_net.log"),
)


def migrate():
    import os
    for old, new in OLD_NAMES:
        try:
            os.stat(new)
            continue
        except OSError:
            pass
        try:
            os.rename(old, new)
        except OSError:
            pass


RELAY_FILE = "/state/burn_helper_relay.json"


def load_relay():
    """The Mac's internet relay {"url", "key"}, learned over USB from the bridge, or None."""
    try:
        with open(RELAY_FILE) as f:
            r = json.loads(f.read())
        if isinstance(r, dict) and str(r.get("url", "")).startswith("https://") and r.get("key"):
            return {"url": str(r["url"]), "key": str(r["key"])}
    except Exception:  # noqa: BLE001
        pass
    return None


def save_relay(r):
    try:
        with open(RELAY_FILE, "w") as f:
            f.write(json.dumps(r))
        return True
    except Exception:  # noqa: BLE001
        return False


KEY_FILE = "/state/burn_helper_key.txt"


def load_key():
    """The bridge's key, learned over USB from the bridge, or None. It opens the bridge's sealed answers; it is never sent."""
    try:
        with open(KEY_FILE) as f:
            k = f.read().strip()
        return k or None
    except Exception:  # noqa: BLE001
        return None


def save_key(k):
    try:
        with open(KEY_FILE, "w") as f:
            f.write(k)
        return True
    except Exception:  # noqa: BLE001
        return False


def load_portal():
    try:
        with open(NET_FILE) as f:
            d = json.loads(f.read())
        if isinstance(d, dict):
            return d
    except Exception:  # noqa: BLE001
        pass
    return {"networks": [], "bridge": ""}


def save_portal(d):
    try:
        import os
        try:
            os.mkdir("/state")
        except OSError:
            pass
        with open(NET_FILE, "w") as f:
            f.write(json.dumps(d))
        return True
    except Exception:  # noqa: BLE001
        return False


def networks():
    """[(ssid, password, source)] in the order to try: phone-added first, then secrets.py."""
    out = []
    for n in load_portal().get("networks", []):
        if isinstance(n, (list, tuple)) and len(n) == 2 and n[0]:
            out.append((n[0], n[1], "phone"))
    s = _secrets()
    if s is not None:
        ssid = getattr(s, "WIFI_SSID", "")
        if ssid:
            out.append((ssid, getattr(s, "WIFI_PASSWORD", ""), "secrets"))
        for n in getattr(s, "WIFI_EXTRA", []) or []:
            if n and n[0]:
                out.append((n[0], n[1], "secrets"))
    seen = []
    uniq = []
    for n in out:
        if n[0] not in seen:
            seen.append(n[0])
            uniq.append(n)
    return uniq


def last_network():
    """The saved network that connected last time (tried first), or None."""
    return load_portal().get("last") or None


def save_last_network(ssid):
    d = load_portal()
    if d.get("last") != ssid:
        d["last"] = ssid
        save_portal(d)


def paired_bridge():
    """The id of the bridge this badge belongs to (learnt over the USB cable), or None."""
    return load_portal().get("paired") or None


def save_paired_bridge(bid):
    d = load_portal()
    if d.get("paired") != bid:
        d["paired"] = bid
        save_portal(d)


def _parse_bridge(v):
    v = (v or "").strip()
    if not v:
        return None
    if v.startswith("http://"):
        v = v[7:]
    v = v.split("/")[0]
    if ":" in v:
        host, port = v.rsplit(":", 1)
        try:
            return (host, int(port))
        except ValueError:
            return None
    return (v, 8787)


def bridge():
    b = _parse_bridge(load_portal().get("bridge", ""))
    if b:
        return b
    s = _secrets()
    return _parse_bridge(getattr(s, "BRIDGE", "") if s else "")
