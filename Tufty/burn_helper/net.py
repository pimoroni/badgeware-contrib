# Networking for the badge: Wi-Fi with fallbacks, bridge discovery and a
# non-blocking HTTP poll. Everything is driven from tick(), called once per
# frame, and nothing here may raise: an exception inside the run() loop would
# drop the badge into the firmware's fatal-error screen.

import json
import seal
import socket
import select
import time

try:
    import network
except ImportError:  # desktop simulator
    network = None

try:
    import errno
    EINPROGRESS = errno.EINPROGRESS
    EAGAIN = errno.EAGAIN
except (ImportError, AttributeError):
    EINPROGRESS = 115
    EAGAIN = 11
# Phones put typographic quotes in network names ("Sam’s iPhone"); a name typed on another
# keyboard has a plain one. Saved names match what is on the air with these made plain.
_QUOTES = (("\u2019", "'"), ("\u2018", "'"), ("\u02bc", "'"), ("\u2032", "'"), ("\u201c", '"'), ("\u201d", '"'))


def plain_quotes(s):
    for a, b in _QUOTES:
        s = s.replace(a, b)
    return s


BEACON_PORT = 47800
POLL_MS = 2500
HTTP_TIMEOUT_MS = 4000
JOIN_TIMEOUT_MS = 12000   # a right password joins in about 3 s; a wrong one hangs in "joining"
RETRY_ALL_MS = 15000
FRESH_MS = 12000
NO_BEACON_MS = 10000
PICK_DELAY_MS = 1500      # after the last UP press on the Wi-Fi page, connect to the one picked
PAIRED_GRACE_MS = 60000   # how long the paired bridge may be quiet before another one will do
RELAY_POLL_MS = 5000      # the internet relay is polled less often than the bridge on the LAN
LOG_FILE = "/state/burn_helper_net.log"
LOG_MAX = 16384

# wlan.status() codes (cyw43) and what they mean to a person
STATUS_TEXT = {0: "idle", 1: "joining", 2: "linked, waiting for IP", 3: "connected",
               -1: "connect failed", -2: "network not found", -3: "wrong password"}
# per-network verdicts after an attempt
OK = "connected"
BAD_PW = "wrong password"
STUCK = "never accepted the badge"
NOT_SEEN = "not visible (5 GHz only / out of range?)"
NO_IP = "joined but no IP address (DHCP)"
FAILED = "connect failed"
UNSEALED = "answer not sealed"    # taken for no bridge: an old bridge, or something else on the network
NEEDS_KEY = "needs its key"      # the bridge seals its answers with a key this badge lacks: plug it into the bridge once


def ticks():
    return time.ticks_ms()


def since(t0):
    return time.ticks_diff(time.ticks_ms(), t0)


class HttpGet:
    """One HTTP/1.0 GET, advanced a little on every step() call."""

    def __init__(self, host, port, path, key=None):
        self.done = False
        self.ok = False
        self.body = None
        self.err = None
        self.t0 = ticks()
        self.buf = b""
        self.sent = False
        self.key = key            # the bridge's key: its answer comes sealed with it (seal.py)
        self.req = ("GET %s HTTP/1.0\r\nHost: %s\r\nConnection: close\r\n\r\n" % (path, host)).encode()
        self.sock = None
        try:
            addr = socket.getaddrinfo(host, port)[0][-1]
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setblocking(False)
            self.sock = s
            try:
                s.connect(addr)
            except OSError as e:
                if e.args[0] not in (EINPROGRESS, EAGAIN):
                    raise
            self.poller = select.poll()
            self.poller.register(s, select.POLLOUT | select.POLLIN)
        except Exception as e:  # noqa: BLE001
            self.fail(e)

    def fail(self, e):
        self.err = e
        self.done = True
        self.close()

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:  # noqa: BLE001
                pass
            self.sock = None

    def step(self):
        if self.done:
            return
        if since(self.t0) > HTTP_TIMEOUT_MS:
            self.fail("timeout")
            return
        try:
            for _sock, ev in self.poller.poll(0):
                if ev & (select.POLLERR | select.POLLHUP) and not ev & select.POLLIN:
                    self.fail("connection refused")
                    return
                if not self.sent and ev & select.POLLOUT:
                    self.sock.send(self.req)
                    self.sent = True
                    self.poller.modify(self.sock, select.POLLIN)
                if self.sent and ev & select.POLLIN:
                    while True:
                        try:
                            chunk = self.sock.recv(1024)
                        except OSError as e:
                            if e.args[0] == EAGAIN:
                                break
                            raise
                        if not chunk:
                            self.finish()
                            return
                        self.buf += chunk
                        if len(self.buf) > 16384:
                            self.fail("response too large")
                            return
        except Exception as e:  # noqa: BLE001
            self.fail(e)

    def finish(self):
        self.close()
        self.done = True
        head, _, body = self.buf.partition(b"\r\n\r\n")
        line = head.split(b"\r\n", 1)[0]
        if b" 403" in line:
            self.err = NEEDS_KEY
            return
        if b" 200 " not in line + b" ":
            self.err = "HTTP " + line.decode()[:24]
            return
        if not seal.is_sealed(body):
            self.err = UNSEALED
            return
        body = seal.unseal(self.key, body)
        if body is None:                  # no key yet, or not this bridge's
            self.err = NEEDS_KEY
            return
        try:
            self.body = json.loads(body)
            self.ok = True
        except Exception as e:  # noqa: BLE001
            self.err = e


class Net:
    """Wi-Fi + bridge link with a diagnosis of every failure (see debug screen)."""

    def __init__(self, networks, bridge=None, hostname="burn-helper", relay=None, last=None, on_join=None,
                 paired=None, key=None):
        self.cands = []
        for n in networks:
            if not n or not n[0]:
                continue
            ssid, psk = n[0], n[1]
            src = n[2] if len(n) > 2 else ""
            self.cands.append({"ssid": ssid, "psk": psk, "src": src, "variant": "", "result": "", "tries": 0})
            if psk != psk.strip():
                # phone keyboards love adding a trailing space; also try without it
                self.cands.append({"ssid": ssid, "psk": psk.strip(), "src": src, "variant": "trimmed",
                                   "result": "", "tries": 0})
        self.networks = self.cands            # truthy when anything is configured
        self.last = last                       # the network that last worked: tried first
        self.on_join = on_join                 # called with a network's name when it connects
        self.order = list(range(len(self.cands)))   # the order to try them in (see _scan)
        self.aired = {}                        # saved-style name -> the name as it is on the air
        self.pick = None                       # the saved network the cursor is on (index into cands)
        self.pick_t = 0
        self.want = []                         # indices to try, only these, until one works or none can
        self.paired = paired                   # id of the bridge this badge belongs to (learnt over USB)
        self.paired_t = None                   # when its beacon was last heard
        self.others = {}                       # other bridges heard on this network: host -> id
        self.fixed_bridge = bridge             # (host, port) or None
        self.bridge = bridge
        self.key = key                         # the bridge's key, learned over USB, opens its sealed answers
        self.relay = relay                     # {"url", "key"} of the Mac's internet relay, or None
        self.rclient = None                    # relay.Client while the relay is in use
        self.rpoll_t0 = None
        self.via = None                        # "lan" or "relay": where the last good status came from
        self.force_relay = False               # testing: ignore the LAN bridge (USB "@RELAY 1")
        self.hostname = hostname
        self.wlan = None
        self.state = "init" if self.cands else "none"   # init|scan|joining|up|down|none
        self.cur = None                        # index into cands
        self.join_t0 = 0
        self.down_t0 = 0
        self.ssid = ""
        self.ip = ""
        self.gw = ""
        self.mac = ""
        self.seen = {}                         # ssid -> (best rssi, channel, access points)
        self.best_bssid = {}                   # ssid -> bssid of its strongest access point
        self.pinned = False                    # current join is pinned to best_bssid
        self.scan_total = 0
        self.scan_t = None
        self.status = None
        self.attempts = 0
        self.up_t = None
        self.udp = None
        self.beacon_t = None
        self.http = None
        self.poll_t0 = None
        self.ok_t = None
        self.data = None
        self.seq = 0
        self.err = ""
        self.http_err = ""
        self.extra_query = ""
        self.log = []
        self.boot_t = ticks()
        self._trim_logfile()
        self.note("boot: %d network candidate(s)" % len(self.cands))

    # -------------------------------------------------- logging
    def note(self, msg):
        line = "%5ds %s" % (since(self.boot_t) // 1000, msg)
        self.log.append(line)
        if len(self.log) > 40:
            self.log.pop(0)
        try:
            with open(LOG_FILE, "a") as f:
                f.write(line + "\n")
        except Exception:  # noqa: BLE001
            pass

    def _trim_logfile(self):
        try:
            import os
            if os.stat(LOG_FILE)[6] > LOG_MAX:
                with open(LOG_FILE) as f:
                    keep = f.read()[-LOG_MAX // 2:]
                with open(LOG_FILE, "w") as f:
                    f.write(keep)
            with open(LOG_FILE, "a") as f:
                f.write("---- app start ----\n")
        except Exception:  # noqa: BLE001
            pass

    # -------------------------------------------------- public
    def tick(self):
        try:
            if self.pick is not None and since(self.pick_t) > PICK_DELAY_MS:
                i, self.pick = self.pick, None
                self.connect_to(i)
            self._wifi()
            if self.state == "up":
                self._discover()
                self._poll()
        except Exception as e:  # noqa: BLE001
            self.err = repr(e)[:40]
            self.note("error: " + self.err)

    def fresh(self):
        return self.ok_t is not None and since(self.ok_t) < FRESH_MS

    def set_relay(self, relay):
        """New relay address and key (they arrive over USB from the bridge)."""
        if relay != self.relay:
            self.relay = relay
            self._close_relay()
            self.note("relay set to %s" % (relay["url"] if relay else "none"))

    def _close_relay(self):
        if self.rclient is not None:
            self.rclient.close()
            self.rclient = None

    def _lan_bridge(self):
        """The bridge on this network, if it is there: fixed, or heard by beacon in the last 10 s."""
        if self.force_relay:
            return None
        if self.fixed_bridge is not None:
            return self.fixed_bridge
        if self.bridge is not None and self.beacon_t is not None and since(self.beacon_t) < NO_BEACON_MS:
            return self.bridge
        return None

    def _use_relay(self):
        return (self.relay is not None and self._lan_bridge() is None and self.up_t is not None
                and (self.force_relay or since(self.up_t) > NO_BEACON_MS))

    def results(self):
        out = {}
        for c in self.cands:
            if c["result"]:
                out[c["ssid"]] = c["result"]
        return out

    def hint(self):
        """One plain-language diagnosis of what is wrong right now."""
        if self.state == "none":
            return "No Wi-Fi saved. Hold B for phone setup."
        if self.state == "up":
            if self.via == "relay" and self.fresh():
                return "All good, through the internet relay."
            if self._use_relay():
                return ("Away from the Mac's network: using the internet relay%s" %
                        (" (%s)" % self.http_err if self.http_err else "..."))
            if self.fixed_bridge is None and self.beacon_t is None and self.up_t is not None \
                    and since(self.up_t) > NO_BEACON_MS:
                return ("On Wi-Fi but no bridge beacon: is the Mac on this same network? "
                        "Plug the badge into the Mac once to set up the internet relay.")
            if self.bridge is not None and not self.fresh() and self.http_err == NEEDS_KEY:
                return ("The bridge at %s wants its key: plug the badge into that computer's USB once."
                        % self.bridge[0])
            if self.bridge is not None and not self.fresh() and self.http_err == UNSEALED:
                return ("%s answered without sealing, so the badge ignores it. Update the bridge, or check "
                        "that this is your bridge." % self.bridge[0])
            if self.bridge is not None and not self.fresh() and self.http_err:
                return "Bridge %s:%d not answering (%s)" % (self.bridge[0], self.bridge[1], self.http_err)
            if self.fresh():
                if self.others:
                    return ("Another bridge is on this network (%s). Only one computer should be the bridge: "
                            "run the join line on that one." % list(self.others)[0])
                return "All good."
            return "Connected, waiting for the bridge..."
        verdicts = [c for c in self.cands if c["result"]]
        if self.seen is not None and self.scan_t is not None and not any(self.heard(c["ssid"]) for c in self.cands):
            return "None of your networks are visible. Badge is 2.4 GHz only."
        for want in (BAD_PW, STUCK, NO_IP, FAILED):
            for c in verdicts:
                if c["result"] == want:
                    if want == STUCK:
                        return ("%s is in range but never let the badge in: almost always a "
                                "wrong password (hold B to retype). Else: WPA2 off or MAC filter." % c["ssid"])
                    if want == BAD_PW:
                        return "%s: wrong password. Hold B to re-enter it." % c["ssid"]
                    if want == NO_IP:
                        return "%s joined but gave no IP address (DHCP)" % c["ssid"]
                    return "%s: connect failed" % c["ssid"]
        if self.state == "scan":
            return "Scanning for networks..."
        return "Joining %s..." % self.ssid

    def label(self):
        """Short caption for the themes (about 26 characters)."""
        if self.state == "none":
            return "NO WI-FI: HOLD B TO SET UP"
        if self.state == "scan":
            return "SCANNING WI-FI..."
        if self.state in ("init", "joining"):
            bad = [c for c in self.cands if c["result"] in (BAD_PW, STUCK)]
            if bad and (since(self.boot_t) // 3000) % 2:
                return "WI-FI FAILING: PRESS B x2"
            return "JOINING %s..." % self.ssid.upper()[:14]
        if self.state == "down":
            return "WI-FI FAILING: PRESS B x2"
        if self.fresh():
            return ""
        if self._use_relay():
            return "REACHING THE RELAY..."
        if self.bridge is None:
            return "SEARCHING FOR BRIDGE..."
        if self.http_err == NEEDS_KEY:
            return "PLUG INTO BRIDGE FOR KEY"
        if self.http_err == UNSEALED:
            return "BRIDGE ANSWER NOT SEALED"
        if not self.fresh():
            return "BRIDGE NOT ANSWERING"
        return ""

    def trouble(self):
        """What label() is about, in a word, for the connection-lost screens' advice: wifi, relay or bridge."""
        if self.state != "up":
            return "wifi"
        if self._use_relay():
            return "relay"
        return "key" if self.http_err == NEEDS_KEY else "bridge"

    def stop(self):
        self._close_udp()
        self._close_relay()
        if self.http:
            self.http.close()
            self.http = None
        if self.wlan:
            try:
                self.wlan.disconnect()
                self.wlan.active(False)
            except Exception:  # noqa: BLE001
                pass
        self.wlan = None
        self.state = "init" if self.cands else "none"
        self.note("wifi stopped")

    def networks_list(self):
        """Indices of the saved networks to show and pick from (a password variant is not a network)."""
        return [i for i, c in enumerate(self.cands) if not c["variant"]]

    def pick_next(self):
        """UP on the Wi-Fi page: move the cursor to the next saved network. It connects there after
        PICK_DELAY_MS with no further press. Starts on the first one."""
        shown = self.networks_list()
        if not shown:
            return
        nxt = shown[0] if self.pick not in shown else shown[(shown.index(self.pick) + 1) % len(shown)]
        self.pick, self.pick_t = nxt, ticks()

    def pick_cancel(self):
        self.pick = None

    def connect_to(self, i):
        """Connect to saved network i now (leaving the current one), whatever order they are normally
        tried in. If it can't be joined, the others are tried as usual."""
        ssid = self.cands[i]["ssid"]
        self.want = [j for j, c in enumerate(self.cands) if c["ssid"] == ssid]
        self.note("you picked %s" % ssid)
        for j in self.want:
            self.cands[j]["result"] = ""
        self._close_udp()
        self._close_relay()
        self.up_t = None
        self.beacon_t = None
        if self.wlan is not None:
            try:
                self.wlan.disconnect()
            except Exception:  # noqa: BLE001
                pass
        self.state = "scan" if self.wlan is not None else "init"

    def rescan(self):
        if self.state not in ("none", "up"):
            self.state = "scan"

    def heard(self, ssid):
        """The name a saved network is on the air under in the last scan (quotes can differ), or None."""
        if ssid in self.seen:
            return ssid
        return self.aired.get(plain_quotes(ssid))

    # -------------------------------------------------- wifi
    def _scan(self):
        self.seen = {}
        self.best_bssid = {}
        self.aired = {}
        try:
            res = self.wlan.scan()
        except Exception as e:  # noqa: BLE001
            self.note("scan failed: %r" % e)
            res = []
        self.scan_total = len(res)
        for r in res:
            try:
                name = r[0].decode()
            except Exception:  # noqa: BLE001
                continue
            if not name:
                continue
            old = self.seen.get(name)
            if old is None or r[3] > old[0]:
                self.best_bssid[name] = r[1]
            if old is None:
                self.seen[name] = (r[3], r[2], 1)
                self.aired[plain_quotes(name)] = name
            else:
                best = old if old[0] >= r[3] else (r[3], r[2], 0)
                self.seen[name] = (best[0], best[1], old[2] + 1)
        self.scan_t = ticks()
        # the network that last worked first, then the saved order
        last = plain_quotes(self.last) if self.last else None
        self.order = sorted(range(len(self.cands)),
                            key=lambda i: (0 if last and plain_quotes(self.cands[i]["ssid"]) == last else 1, i))
        mine = []
        for c in self.cands:
            info = self.seen.get(self.heard(c["ssid"]) or "")
            if c["variant"]:
                continue
            if info:
                mine.append("%s ch%d %ddBm" % (c["ssid"], info[1], info[0]))
            else:
                mine.append("%s NOT VISIBLE" % c["ssid"])
                c["result"] = NOT_SEEN
        self.note("scan: %d networks; %s" % (self.scan_total, "; ".join(mine)))

    def _next(self, after=None):
        """Index of the next visible candidate in try order after `after` (an index), or the first."""
        order = self.want or self.order
        start = 0 if after is None or after not in order else order.index(after) + 1
        for i in order[start:]:
            if self.heard(self.cands[i]["ssid"]) is not None:
                return i
        return None

    def _join(self, i, pin=True):
        c = self.cands[i]
        self.cur = i
        self.ssid = self.heard(c["ssid"]) or c["ssid"]     # join under the exact name on the air
        c["tries"] += 1
        self.attempts += 1
        try:
            self.wlan.disconnect()
        except Exception:  # noqa: BLE001
            pass
        # Combined 2.4/5 GHz and mesh networks share one name: the radio only hears the 2.4 GHz
        # side, so aim at its strongest access point first, then let it pick any.
        bssid = self.best_bssid.get(self.ssid) if pin else None
        self.pinned = bssid is not None
        try:
            if bssid is not None:
                self.wlan.connect(self.ssid, c["psk"], bssid=bssid)
            else:
                self.wlan.connect(self.ssid, c["psk"])
        except Exception as e:  # noqa: BLE001
            self.pinned = False
            self.note("pinned join not accepted (%r); joining by name" % (e,))
            self.wlan.connect(self.ssid, c["psk"])
        self.join_t0 = ticks()
        self.status = None
        self.state = "joining"
        self.note("join %s%s%s (password %d chars)" % (c["ssid"], " [trimmed]" if c["variant"] else "",
                                                       " [strongest AP]" if self.pinned else "", len(c["psk"])))

    def _verdict(self, st, timed_out):
        if st == network.STAT_WRONG_PASSWORD:
            return BAD_PW
        if st == network.STAT_NO_AP_FOUND:
            return NOT_SEEN
        if st == network.STAT_CONNECT_FAIL:
            return FAILED
        if timed_out and st == 2:
            return NO_IP
        if timed_out:
            return STUCK
        return ""

    def _wifi(self):
        if self.state == "none" or network is None:
            return
        if self.wlan is None:
            try:
                network.hostname(self.hostname)
            except Exception:  # noqa: BLE001
                pass
            self.wlan = network.WLAN(network.STA_IF)
            self.wlan.active(True)
            try:
                import binascii
                self.mac = binascii.hexlify(self.wlan.config("mac"), ":").decode()
            except Exception:  # noqa: BLE001
                self.mac = "?"
            if self.wlan.isconnected():
                self._up()
                return
            self.state = "scan"        # scan on the next frame so "SCANNING" gets drawn first
            return
        if self.state == "scan":
            self._scan()
            i = self._next()
            if i is None and self.want:
                self.note("%s is not in range: back to the others" % self.cands[self.want[0]]["ssid"])
                self.want = []
                i = self._next()
            if i is None:
                self.state = "down"
                self.down_t0 = ticks()
                self.note("none of the saved networks are visible; retry in %ds" % (RETRY_ALL_MS // 1000))
            else:
                self._join(i)
            return
        if self.state == "up":
            if not self.wlan.isconnected():
                self.note("lost connection to %s" % self.ssid)
                self._close_udp()
                self.up_t = None
                self.state = "scan"
            return
        if self.state == "down":
            if since(self.down_t0) > RETRY_ALL_MS:
                self.state = "scan"
            return
        # joining
        if self.wlan.isconnected():
            self._up()
            return
        st = self.wlan.status()
        if st != self.status:
            self.note("status %d (%s) after %dms" % (st, STATUS_TEXT.get(st, "?"), since(self.join_t0)))
            self.status = st
        timed_out = since(self.join_t0) > JOIN_TIMEOUT_MS
        verdict = self._verdict(st, timed_out)
        if verdict:
            c = self.cands[self.cur]
            info = self.seen.get(self.ssid)
            if self.pinned and verdict in (STUCK, FAILED) and info and info[2] > 1:
                self.note("%s: strongest AP did not accept; trying any AP" % c["ssid"])
                self._join(self.cur, pin=False)
                return
            c["result"] = verdict
            self.note("%s: %s" % (c["ssid"], verdict))
            nxt = self._next(self.cur)
            if nxt is None and self.want:
                self.note("could not join the one you picked: back to the others")
                self.want = []
                self.state = "scan"
                return
            if nxt is not None:
                self._join(nxt)
            else:
                self.state = "down"
                self.down_t0 = ticks()
                try:
                    self.wlan.disconnect()
                except Exception:  # noqa: BLE001
                    pass
                self.note("all networks failed; retry in %ds" % (RETRY_ALL_MS // 1000))

    def _up(self):
        self.state = "up"
        self.want = []
        self.up_t = ticks()
        try:
            cfg = self.wlan.ifconfig()
            self.ip = cfg[0]
            self.gw = cfg[2]
        except Exception:  # noqa: BLE001
            self.ip = "?"
        if self.cur is not None:
            self.cands[self.cur]["result"] = OK
            name = self.cands[self.cur]["ssid"]
            if name != self.last:
                self.last = name
                if self.on_join is not None:
                    try:
                        self.on_join(name)
                    except Exception:  # noqa: BLE001
                        pass
        self.note("connected to %s: ip %s gateway %s" % (self.ssid, self.ip, self.gw))

    # -------------------------------------------------- diagnostics
    def dump(self):
        """Everything the debug screen knows, as text lines (also sent over USB)."""
        out = ["state %s  attempts %d  mac %s" % (self.state, self.attempts, self.mac)]
        if self.state == "up":
            out.append("ssid %s  ip %s  gw %s" % (self.ssid, self.ip, self.gw))
        elif self.status is not None:
            out.append("%s %s: status %d (%s) for %ds" % (
                "joining" if self.state == "joining" else "last join", self.ssid, self.status,
                STATUS_TEXT.get(self.status, "?"), since(self.join_t0) // 1000))
        for c in self.cands:
            info = self.seen.get(self.heard(c["ssid"]) or "")
            vis = "ch%d %ddBm x%d" % (info[1], info[0], info[2]) if info else "not seen"
            out.append("net %s%s [%s] pw %d chars%s | %s | tries %d | %s" % (
                c["ssid"], " (trimmed)" if c["variant"] else "", c["src"] or "?", len(c["psk"]),
                " ENDS WITH SPACE" if c["psk"] != c["psk"].rstrip() else "", vis, c["tries"], c["result"] or "-"))
        out.append("scan: %d networks visible" % self.scan_total)
        if self.paired:
            out.append("paired with bridge %s%s" % (self.paired, "" if self.paired_t is None else
                                                    ", heard %ds ago" % (since(self.paired_t) // 1000)))
        for host, bid in self.others.items():
            out.append("another bridge at %s (id %s) ignored: run the join line there" % (host, bid or "?"))
        b = self.bridge
        out.append("bridge %s  beacon %s  last ok %s  http %s" % (
            "%s:%d" % b if b else "unknown",
            "never" if self.beacon_t is None else "%ds ago" % (since(self.beacon_t) // 1000),
            "never" if self.ok_t is None else "%ds ago" % (since(self.ok_t) // 1000),
            self.http_err or "-"))
        if self.relay is not None:
            c = self.rclient
            out.append("relay %s  via %s  handshakes %d  %s" % (
                self.relay["url"].split("://", 1)[-1].split(".", 1)[0], self.via or "-",
                c.handshakes if c else 0, "forced" if self.force_relay else ""))
        out.append("hint: " + self.hint())
        return out

    # -------------------------------------------------- discovery
    def _close_udp(self):
        if self.udp is not None:
            try:
                self.udp.close()
            except Exception:  # noqa: BLE001
                pass
            self.udp = None

    def _discover(self):
        if self.udp is None:
            try:
                u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    u.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                except Exception:  # noqa: BLE001
                    pass
                u.bind(("0.0.0.0", BEACON_PORT))
                u.setblocking(False)
                self.udp = u
            except Exception as e:  # noqa: BLE001
                self.err = "udp " + repr(e)[:30]
                return
        for _ in range(4):
            try:
                data, addr = self.udp.recvfrom(64)
            except OSError:
                return
            if data.startswith(b"TUFTYBRIDGE"):
                parts = data.split()
                try:
                    port = int(parts[2])
                except Exception:  # noqa: BLE001
                    port = 8787
                bid = parts[3].decode() if len(parts) > 3 else ""
                host = addr[0] if isinstance(addr, tuple) else socket.inet_ntop(socket.AF_INET, addr[4:8])
                self._beacon(host, port, bid)

    def _beacon(self, host, port, bid):
        """A bridge announced itself. Stay with one bridge: the paired one when it is around, else
        the one already in use while it keeps announcing itself, so two bridges on one network
        can't pull the badge back and forth."""
        if self.fixed_bridge is not None:
            self.beacon_t = ticks()
            return
        mine = (host, port) == self.bridge
        if self.paired and bid == self.paired:
            self.paired_t = ticks()
        elif self.paired and (self.paired_t is None or since(self.paired_t) < PAIRED_GRACE_MS) \
                and (self.paired_t is not None or self.up_t is None or since(self.up_t) < PAIRED_GRACE_MS):
            self._other(host, bid)          # not ours, and ours was heard lately (or may still be)
            return
        elif not mine and self.bridge is not None and self.beacon_t is not None \
                and since(self.beacon_t) < NO_BEACON_MS:
            self._other(host, bid)          # keep the one in use while it is still there
            return
        if not mine:
            self.note("using the bridge at %s:%d%s" % (host, port, (" (id %s)" % bid) if bid else ""))
        self.bridge = (host, port)
        self.beacon_t = ticks()

    def _other(self, host, bid):
        if host not in self.others:
            self.note("another bridge at %s%s: ignored (the badge talks to one bridge)"
                      % (host, (" (id %s)" % bid) if bid else ""))
        self.others[host] = bid

    # -------------------------------------------------- polling
    def _poll(self):
        if self._use_relay():
            self._poll_relay()
            return
        self._close_relay()
        if self.http is not None:
            self.http.step()
            if self.http.done:
                if self.http.ok and isinstance(self.http.body, dict):
                    if self.ok_t is None:
                        self.note("first status from bridge %s:%d" % self.bridge)
                    self.data = self.http.body
                    self.via = "lan"
                    self.ok_t = ticks()
                    self.seq += 1
                    self.err = ""
                    self.http_err = ""
                else:
                    e = str(self.http.err)[:40]
                    if e != self.http_err:
                        self.note("bridge poll failed: " + e)
                    self.http_err = e
                self.http = None
            return
        if self.bridge is None:
            return
        if self.poll_t0 is not None and since(self.poll_t0) < POLL_MS:
            return
        self.poll_t0 = ticks()
        self.http = HttpGet(self.bridge[0], self.bridge[1], "/status" + self.extra_query, self.key)

    def _poll_relay(self):
        """Away from home: the same status, over HTTPS through the Mac's Tailscale Funnel."""
        if self.rclient is None:
            import relay
            self.rclient = relay.Client(self.relay["url"], self.relay["key"])
            self.note("no bridge on this network: using the internet relay")
        c = self.rclient
        if not c.done:
            c.step()
            if c.done:
                if c.ok and isinstance(c.body, dict):
                    if self.via != "relay":
                        self.note("first status through the internet relay")
                    self.data = c.body
                    self.via = "relay"
                    self.ok_t = ticks()
                    self.seq += 1
                    self.err = ""
                    self.http_err = ""
                else:
                    e = str(c.err)[:40]
                    if e != self.http_err:
                        self.note("relay poll failed: " + e)
                    self.http_err = e
            return
        if self.rpoll_t0 is not None and since(self.rpoll_t0) < RELAY_POLL_MS:
            return
        self.rpoll_t0 = ticks()
        c.start("/status")
