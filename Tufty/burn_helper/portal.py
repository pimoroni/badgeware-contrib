# Phone setup portal: the badge becomes a Wi-Fi hotspot with a tiny web form.
#
# Join the hotspot from your phone (scan the QR code on screen), open
# http://192.168.4.1 and add a Wi-Fi network (home, office or your phone's own
# hotspot) and optionally a fixed bridge address. Saved to
# /state/burn_helper_net.json, then the badge restarts and uses it.

import socket
import time
import machine
import network
import config
import gfx

PAGE = """<!doctype html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<title>Burn Helper setup</title><style>body{font-family:-apple-system,system-ui,sans-serif;max-width:440px;margin:24px auto;padding:0 16px;background:#111;color:#eee}
input,button{font-size:18px;width:100%;box-sizing:border-box;padding:10px;margin:6px 0 14px;border-radius:8px;border:1px solid #555;background:#222;color:#eee}
button{background:#d97757;border:0;color:#111;font-weight:600}small,.dim{color:#999}li{margin:6px 0}
.net{display:flex;justify-content:space-between;padding:10px;margin:4px 0;border-radius:8px;background:#1d1d1d;cursor:pointer}
.bad{color:#ff8a80}.ok{color:#8be38b}label.cb{display:flex;gap:8px;align-items:center;margin:-8px 0 14px}label.cb input{width:auto;margin:0}</style></head><body>
<h2>Burn Helper setup</h2>
<p class=dim>The badge only does <b>2.4 GHz</b> Wi-Fi with a WPA2 password. These are the networks it can hear right now; tap one to use it.</p>
%SCAN%
<form method=post action=/save><label>Wi-Fi name (SSID)<input id=ssid name=ssid required autocapitalize=none autocorrect=off spellcheck=false></label>
<label>Password<input id=psk name=psk type=password autocapitalize=none autocorrect=off spellcheck=false></label>
<label class=cb><input type=checkbox onclick="document.getElementById('psk').type=this.checked?'text':'password'">Show password (check it is exactly right)</label>
<label>Bridge address <small>(optional, e.g. 192.168.1.20:8787; blank = auto-discover)</small><input name=bridge value="%BRIDGE%" autocapitalize=none autocorrect=off spellcheck=false></label>
<button>Save and connect</button></form><h3>Saved networks</h3><ul>%LIST%</ul>
<form method=post action=/forget><button style="background:#444;color:#eee">Forget saved networks</button></form>
<p class=dim>Badge MAC address: %MAC% (add it to your router's allow list if it filters devices).</p></body></html>"""

DONE = """<!doctype html><html><head><meta name=viewport content="width=device-width,initial-scale=1"></head>
<body style="font-family:system-ui;background:#111;color:#eee;padding:24px"><h2>Saved.</h2><p>The badge is joining the network now and shows the result on its screen. Reconnect your phone to your usual Wi-Fi.</p></body></html>"""


def _unquote(s):
    s = s.replace("+", " ")
    out = b""
    i = 0
    b = s.encode()
    while i < len(b):
        if b[i] == 37 and i + 2 < len(b):
            try:
                out += bytes([int(b[i + 1:i + 3], 16)])
                i += 3
                continue
            except ValueError:
                pass
        out += b[i:i + 1]
        i += 1
    return out.decode()


def _form(body):
    d = {}
    for part in body.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            d[_unquote(k)] = _unquote(v)
    return d


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")


class Portal:
    def __init__(self, results=None, notice=""):
        self.results = results or {}
        self.notice = notice
        self.scan = []
        self.bssids = {}
        self.mac = "?"
        try:
            import binascii
            sta = network.WLAN(network.STA_IF)
            sta.active(True)
            self.mac = binascii.hexlify(sta.config("mac"), ":").decode()
            best = {}
            for r in sta.scan():
                name = r[0].decode()
                if name and (name not in best or r[3] > best[name][0]):
                    best[name] = (r[3], r[2])
                    self.bssids[name] = r[1]
            self.scan = sorted(best.items(), key=lambda kv: -kv[1][0])[:12]
        except Exception:  # noqa: BLE001
            pass
        uid = machine.unique_id()
        # First-time setup (no Wi-Fi saved yet) uses an open hotspot so there is nothing to type or
        # scan past; once a network is saved the hotspot gets a password.
        self.open = not config.networks()
        # 8 digits: the shortest WPA2 password, and easy to type on a phone keypad. It comes from
        # the chip id, so it stays the same for this badge and a phone that saved it keeps working.
        n = ((uid[-4] << 24) | (uid[-3] << 16) | (uid[-2] << 8) | uid[-1]) % 100000000
        self.psk = "" if self.open else "%08d" % n
        # The screen is small: use the full hotspot name when it fits beside the QR code,
        # otherwise a shorter real name, so what is shown is exactly what the phone sees.
        self.ssid = "BurnHelper-%02X%02X" % (uid[-2], uid[-1])
        self.qr = self._make_qr()
        if not self._fits():
            self.ssid = "Burn-%02X%02X" % (uid[-2], uid[-1])
            self.qr = self._make_qr()
        self.ap = network.WLAN(network.AP_IF)
        if self.open:
            try:
                self.ap.config(ssid=self.ssid, security=0)
            except Exception:  # noqa: BLE001
                self.ap.config(ssid=self.ssid)
        else:
            try:
                self.ap.config(ssid=self.ssid, key=self.psk)
            except Exception:  # noqa: BLE001
                self.ap.config(ssid=self.ssid, password=self.psk)
        self.ap.active(True)
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("0.0.0.0", 80))
        self.srv.listen(2)
        self.srv.setblocking(False)
        self.phase = "serve"       # serve -> wait -> joining -> result
        self.due = 0
        self.saved = False
        self.outcome = None        # "ok" or "fail" when the join attempt is over
        self.lines = []
        self.sta = None
        self.new_ssid = ""
        self.new_psk = ""
        self.j0 = 0
        self.t0 = time.ticks_ms()

    def _make_qr(self):
        if self.open:
            return screen.qr("WIFI:T:nopass;S:%s;;" % self.ssid, 0, 0, 1)
        return screen.qr("WIFI:T:WPA;S:%s;P:%s;;" % (self.ssid, self.psk), 0, 0, 1)

    def _layout(self):
        """(qr scale, x of the text column) used by draw()."""
        s = 3 if self.qr.width * 3 <= 84 else 2
        return s, self.qr.width * s + 14

    def _fits(self):
        return gfx.width(self.ssid, font.sins) <= 160 - self._layout()[1] - 2

    def ip(self):
        try:
            return self.ap.ifconfig()[0]
        except Exception:  # noqa: BLE001
            return "192.168.4.1"

    def _begin_join(self, now):
        """Leave hotspot mode and try the network that was just saved, on the badge itself."""
        self.close()
        self.lines = ["SAVED", self.new_ssid]
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(True)
        bssid = self.bssids.get(self.new_ssid)
        try:
            if bssid:
                self.sta.connect(self.new_ssid, self.new_psk, bssid=bssid)
            else:
                self.sta.connect(self.new_ssid, self.new_psk)
        except Exception:  # noqa: BLE001
            self.sta.connect(self.new_ssid, self.new_psk)
        self.j0 = now
        self.phase = "joining"

    def _poll_join(self, now):
        waited = time.ticks_diff(now, self.j0)
        if self.sta.isconnected():
            self.lines = ["CONNECTED TO", self.new_ssid, "IP " + self.sta.ifconfig()[0], "SUCCESS!"]
            self.outcome, self.phase, self.due = "ok", "result", time.ticks_add(now, 3500)
            return
        st = self.sta.status()
        if waited > 12000 or st < 0:
            why = "NETWORK NOT SEEN" if st == -2 else "WRONG PASSWORD?"
            try:
                self.sta.disconnect()
            except Exception:  # noqa: BLE001
                pass
            self.lines = ["COULD NOT JOIN", self.new_ssid, why, "TRY AGAIN..."]
            self.outcome, self.phase, self.due = "fail", "result", time.ticks_add(now, 4500)

    def tick(self):
        now = time.ticks_ms()
        if self.phase == "wait":
            if time.ticks_diff(now, self.due) > 0:
                self._begin_join(now)
            return
        if self.phase == "joining":
            self._poll_join(now)
            return
        if self.phase == "result":
            if time.ticks_diff(now, self.due) > 0:
                self.phase = "done"
            return
        if self.phase == "done":
            return
        try:
            cl, _ = self.srv.accept()
        except OSError:
            return
        try:
            cl.settimeout(3)
            self.handle(cl)
        except Exception:  # noqa: BLE001
            pass
        try:
            cl.close()
        except Exception:  # noqa: BLE001
            pass

    def handle(self, cl):
        req = b""
        while b"\r\n\r\n" not in req and len(req) < 4096:
            chunk = cl.recv(512)
            if not chunk:
                break
            req += chunk
        head, _, body = req.partition(b"\r\n\r\n")
        lines = head.decode().split("\r\n")
        method, path = (lines[0].split(" ") + ["", ""])[:2]
        length = 0
        for ln in lines[1:]:
            if ln.lower().startswith("content-length:"):
                length = int(ln.split(":", 1)[1].strip() or 0)
        while len(body) < min(length, 2048):
            chunk = cl.recv(512)
            if not chunk:
                break
            body += chunk
        d = config.load_portal()
        if method == "POST" and path == "/save":
            f = _form(body.decode())
            ssid = f.get("ssid", "").strip()
            if ssid:
                nets = [n for n in d.get("networks", []) if n[0] != ssid]
                # phone keyboards add trailing spaces; WPA passphrases never need them
                d["networks"] = [[ssid, f.get("psk", "").strip()]] + nets[:4]
            d["bridge"] = f.get("bridge", "").strip()
            config.save_portal(d)
            if ssid:
                self.new_ssid = ssid
                self.new_psk = f.get("psk", "").strip()
                self.saved = True
                self.phase = "wait"      # let the "Saved" page reach the phone, then join
                self.due = time.ticks_add(time.ticks_ms(), 1500)
            self.send(cl, DONE)
            return
        if method == "POST" and path == "/forget":
            config.save_portal({"networks": [], "bridge": d.get("bridge", "")})
            d = config.load_portal()
        items = ""
        for n in d.get("networks", []):
            r = self.results.get(n[0], "")
            cls = "ok" if r == "connected" else "bad"
            items += "<li>%s <small>(password %d characters)</small>%s</li>" % (
                _esc(n[0]), len(n[1]), " <span class=%s>last try: %s</span>" % (cls, _esc(r)) if r else "")
        items = items or "<li><small>none</small></li>"
        scan = ""
        for name, (rssi, ch) in self.scan:
            bars = "&#9679;" * (4 if rssi > -60 else 3 if rssi > -70 else 2 if rssi > -80 else 1)
            scan += ("<div class=net onclick=\"document.getElementById('ssid').value=this.dataset.n;"
                     "document.getElementById('psk').focus()\" data-n=\"%s\"><span>%s</span>"
                     "<small>%s ch%d</small></div>") % (_esc(name), _esc(name), bars, ch)
        scan = scan or "<p class=dim>(scan found nothing)</p>"
        page = PAGE.replace("%LIST%", items).replace("%BRIDGE%", _esc(d.get("bridge", "")))
        self.send(cl, page.replace("%SCAN%", scan).replace("%MAC%", _esc(self.mac)))

    def send(self, cl, html):
        data = html.encode()
        cl.send(b"HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % len(data))
        i = 0
        while i < len(data):
            i += cl.send(data[i:i + 1024])

    def close(self):
        try:
            self.srv.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.ap.active(False)
        except Exception:  # noqa: BLE001
            pass

    def draw_status(self, t):
        ok = self.outcome == "ok"
        bad = self.outcome == "fail"
        colour = (110, 220, 120) if ok else (255, 110, 100) if bad else (250, 200, 120)
        gfx.box(0, 0, 160, 120, (20, 18, 24))
        gfx.box(0, 0, 160, 13, colour)
        gfx.text("WI-FI CONNECT", 4, -1, (20, 18, 24), font.sins)
        lines = list(self.lines)
        if self.phase == "wait":
            lines = ["SAVED", self.new_ssid, "LEAVING SETUP MODE..."]
        elif self.phase == "joining":
            dots = "." * (1 + (time.ticks_diff(t, self.j0) // 400) % 3)
            lines = lines + ["JOINING" + dots, "%d S" % (time.ticks_diff(t, self.j0) // 1000)]
        y = 20
        for i, line in enumerate(lines):
            last = i == len(lines) - 1 and self.outcome
            gfx.text(line[:24], 6, y, colour if last else (230, 230, 230), font.sins)
            y += 12
        if self.outcome:
            msg = "BACK TO MAIN SCREEN..." if ok else "BACK TO SETUP..."
            gfx.text(msg, 6, 106, (150, 150, 160), font.sins)

    def draw(self, t):
        if self.phase != "serve":
            self.draw_status(t)
            return
        gfx.box(0, 0, 160, 120, (20, 18, 24))
        gfx.box(0, 0, 160, 13, (217, 119, 87))
        gfx.text("PHONE SETUP", 4, -1, (20, 18, 24), font.sins)
        q = self.qr
        s, x = self._layout()
        qs = q.width * s
        gfx.box(2, 18, qs + 8, qs + 8, (255, 255, 255))
        screen.blit(q, rect(6, 22, qs, qs))
        y = 15
        for line in ("1. SCAN TO JOIN", "   WI-FI:", self.ssid, "2. OPEN", self.ip(), "3. ADD NETWORK"):
            gfx.text(line, x, y, (230, 230, 230), font.sins)
            y += 10
        if self.notice:
            gfx.text(self.notice[:26], 4, 82, (255, 110, 100), font.sins)
        gfx.text("NO WIFI PASS NEEDED" if self.open else "WIFI PASS " + self.psk, 4, 94, (250, 200, 120), font.sins)
        gfx.text("PRESS B TO CANCEL", 4, 106, (150, 150, 160), font.sins)
