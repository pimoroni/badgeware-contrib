# HTTPS to the bridge's internet relay (Tailscale Funnel, see bridge/relay.py), used when the
# badge is away from the Mac's network. It must never stall the animation, so: the TCP
# connect is non-blocking, the TLS handshake runs a step at a time between frames (the
# longest step measured on the badge is about 0.3 s), and the connection is kept open so
# later polls skip the handshake. The certificate is checked against Let's Encrypt's roots
# before the key is sent. Nothing here may raise; errors end up in .err.

import json
import socket
import select
import ssl
import time

try:
    import errno
    AGAIN = (errno.EAGAIN, errno.EINPROGRESS, errno.ETIMEDOUT)
except (ImportError, AttributeError):
    AGAIN = (11, 115, 110)

TIMEOUT_MS = 10000


def _ticks():
    return time.ticks_ms()


def _dechunk(body):
    """Body of a chunked HTTP response, or None while it is still incomplete."""
    out = b""
    while True:
        line, sep, rest = body.partition(b"\r\n")
        if not sep:
            return None
        try:
            n = int(line.split(b";")[0], 16)
        except ValueError:
            return None
        if n == 0:
            return out
        if len(rest) < n + 2:
            return None
        out += rest[:n]
        body = rest[n + 2:]


class Client:
    def __init__(self, url, key):
        self.host = url.split("://", 1)[-1].split("/", 1)[0]
        self.key = key
        self.raw = None
        self.sock = None
        self.poller = None
        self.state = "idle"            # idle | connecting | sending | reading
        self.done = True
        self.ok = False
        self.body = None
        self.err = None
        self.t0 = 0
        self.out = b""
        self.buf = b""
        self.handshakes = 0

    def close(self):
        for s in (self.sock, self.raw):
            if s is not None:
                try:
                    s.close()
                except Exception:  # noqa: BLE001
                    pass
        self.sock = self.raw = self.poller = None
        self.state = "idle"

    def _fail(self, why):
        self.close()
        self.err = why
        self.done = True

    def start(self, path):
        self.done = self.ok = False
        self.body = self.err = None
        self.t0 = _ticks()
        self.buf = b""
        self.out = ("GET %s HTTP/1.1\r\nHost: %s\r\nX-Burn-Helper-Key: %s\r\nConnection: keep-alive\r\n\r\n"
                    % (path, self.host, self.key)).encode()
        if self.sock is None:
            if time.localtime()[0] < 2025:
                # TLS checks certificate dates, and the badge's clock starts in 2021 after a power
                # cycle: set it from an internet time server first (about 50 ms)
                try:
                    import ntptime
                    ntptime.settime()
                except Exception as e:  # noqa: BLE001
                    self._fail("clock: %r" % (e,))
                    return
            try:
                addr = socket.getaddrinfo(self.host, 443)[0][-1]    # DNS, about 30 ms
                s = socket.socket()
                s.setblocking(False)
                try:
                    s.connect(addr)
                except OSError as e:
                    if e.args[0] not in AGAIN:
                        raise
                self.raw = s
                self.poller = select.poll()
                self.poller.register(s, select.POLLOUT)
                self.state = "connecting"
            except Exception as e:  # noqa: BLE001
                self._fail("connect: %r" % (e,))
        else:
            self.state = "sending"

    def step(self):
        if self.done:
            return
        if time.ticks_diff(_ticks(), self.t0) > TIMEOUT_MS:
            self._fail("timeout")
            return
        try:
            if self.state == "connecting":
                ev = self.poller.poll(0)
                if not ev:
                    return
                if ev[0][1] & (select.POLLERR | select.POLLHUP):
                    self._fail("connection refused")
                    return
                import certs
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ctx.verify_mode = ssl.CERT_REQUIRED
                ctx.load_verify_locations(cadata=certs.ROOTS)
                self.sock = ctx.wrap_socket(self.raw, server_hostname=self.host, do_handshake_on_connect=False)
                self.handshakes += 1
                self.state = "sending"
            elif self.state == "sending":
                n = self.sock.write(self.out)       # also drives the handshake until it is done
                if n:
                    self.out = self.out[n:]
                if not self.out:
                    self.state = "reading"
            elif self.state == "reading":
                for _ in range(4):
                    chunk = self.sock.read(1024)
                    if chunk is None:
                        return
                    if chunk == b"":
                        self._fail("relay closed the connection")
                        return
                    self.buf += chunk
                    if len(self.buf) > 16384:
                        self._fail("response too large")
                        return
                    if self._parse():
                        return
        except OSError as e:
            if e.args and e.args[0] in AGAIN:
                return
            self._fail("tls: %r" % (e,))
        except Exception as e:  # noqa: BLE001
            self._fail(repr(e)[:40])

    def _parse(self):
        head, sep, body = self.buf.partition(b"\r\n\r\n")
        if not sep:
            return False
        lines = head.split(b"\r\n")
        length, chunked, close = None, False, False
        for ln in lines[1:]:
            k, _, v = ln.partition(b":")
            k, v = k.strip().lower(), v.strip().lower()
            if k == b"content-length":
                length = int(v)
            elif k == b"transfer-encoding" and b"chunked" in v:
                chunked = True
            elif k == b"connection" and v == b"close":
                close = True
        if chunked:
            data = _dechunk(body)
            if data is None:
                return False
        else:
            if length is None or len(body) < length:
                return False
            data = body[:length]
        self.buf = b""
        self.done = True
        self.state = "idle"
        if b" 200 " not in lines[0] + b" ":
            # a wrong or old key gets 404: the relay says nothing to strangers
            self.err = "HTTP " + lines[0].decode()[9:24]
        else:
            try:
                self.body = json.loads(data)
                self.ok = True
            except ValueError as e:
                self.err = repr(e)[:40]
        if close:
            self.close()
        return True
