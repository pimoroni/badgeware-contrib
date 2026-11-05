"""Sealing: what the bridge and the computers, badge and phone around it send each other on the
network, encrypted and signed with the bridge's key, so someone watching the network sees neither
what you are working on nor the key, and can't change or replay a message.

    box = seal(key, data)        data: bytes -> MAGIC + nonce(16) + ciphertext + tag(32)
    data = unseal(key, box)      bytes, or None when the box is not sealed with this key

The cipher is HMAC-SHA256 in counter mode, and the tag is HMAC-SHA256 over everything before
it (encrypt-then-MAC), with separate keys derived from the bridge's key for each. Only SHA-256 is
needed, which the badge's MicroPython has and Python's standard library has, so the bridge needs
no extra packages. The phone panel does the same in JavaScript (burn_helper_bridge.PAGE).

This file is the same on the bridge (bridge/seal.py) and the badge (badge/apps/burn_helper/
seal.py); tools/sim/test_seal.py checks that they match.
"""
import hashlib
import os

try:
    import binascii
except ImportError:  # pragma: no cover
    binascii = None

MAGIC = b"BHS1"
NONCE = 16
TAG = 32
_cache = {}


def _pads(key):
    k = key + bytes(64 - len(key))
    return bytes(b ^ 0x36 for b in k), bytes(b ^ 0x5C for b in k)


def hmac256(key, msg, pads=None):
    """HMAC-SHA256 (RFC 2104), written out: the badge's MicroPython has no hmac module."""
    ipad, opad = pads or _pads(key)
    inner = hashlib.sha256(ipad)
    inner.update(msg)
    outer = hashlib.sha256(opad)
    outer.update(inner.digest())
    return outer.digest()


def keys(key):
    """(encryption pads, signing pads) for the bridge's key, given as hex. Kept once worked out."""
    if key not in _cache:
        raw = binascii.unhexlify(key) if len(key) % 2 == 0 and _hexish(key) else key.encode()
        _cache.clear()
        _cache[key] = (_pads(hmac256(raw, b"burn-helper seal enc")), _pads(hmac256(raw, b"burn-helper seal mac")))
    return _cache[key]


def _hexish(s):
    for c in s:
        if c not in "0123456789abcdefABCDEF":
            return False
    return True


def _stream(pads, nonce, data):
    out = bytearray(len(data))
    i = 0
    n = 0
    while i < len(data):
        block = hmac256(None, nonce + n.to_bytes(4, "big"), pads)
        for j in range(min(32, len(data) - i)):
            out[i + j] = data[i + j] ^ block[j]
        i += 32
        n += 1
    return bytes(out)


def same(a, b):
    """a == b without stopping at the first difference (so timing gives nothing away)."""
    if len(a) != len(b):
        return False
    d = 0
    for x, y in zip(a, b):
        d |= x ^ y
    return d == 0


def is_sealed(box):
    return isinstance(box, (bytes, bytearray)) and box[:len(MAGIC)] == MAGIC


def seal(key, data, nonce=None):
    enc, mac = keys(key)
    nonce = nonce or os.urandom(NONCE)
    body = MAGIC + nonce + _stream(enc, nonce, data)
    return body + hmac256(None, body, mac)


def unseal(key, box):
    if not key or not is_sealed(box) or len(box) < len(MAGIC) + NONCE + TAG:
        return None
    enc, mac = keys(key)
    body, tag = box[:-TAG], box[-TAG:]
    if not same(hmac256(None, body, mac), tag):
        return None
    nonce = body[len(MAGIC):len(MAGIC) + NONCE]
    return _stream(enc, nonce, body[len(MAGIC) + NONCE:])


def envelope(key, d):
    """A message to post to the bridge, sealed with the time it was sent: the bridge takes each
    one once, and only within a couple of minutes of then."""
    import json
    import time
    return seal(key, json.dumps({"t": int(time.time()), "d": d}).encode())


def reply(key, raw):
    """The bridge's answer as a dict; None unless it is sealed with this key."""
    import json
    raw = unseal(key, raw)
    if raw is None:
        return None
    try:
        d = json.loads(raw.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError, AttributeError):
        return None
    return d if isinstance(d, dict) else None
