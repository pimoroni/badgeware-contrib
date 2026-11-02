# Protocollo firmato badge <-> dongle (versione 2).
#
# Nessuna dipendenza dalle API Badgeware: gira anche in CPython, cosi' i test
# su PC (presentator_dongle/tools/) usano esattamente questo codice.
# Deve restare allineato con presentator_dongle/src/proto_core.h.
#
# Caratteristiche GATT (servizio b3bb28a0-5c30-4245-9c7d-2ee9a9e560f9):
#   comando  ed860c12-...  NOTIFY  badge -> dongle, messaggi divisi in pezzi
#   stato    1d2189ac-...  WRITE   dongle -> badge, un messaggio per scrittura
#
# Pezzi (notify): byte 0 = bit7 INIZIO | indice 0-127 (cresce di 1, modulo 128),
#   poi i byte del messaggio. Un pezzo con INIZIO azzera il messaggio in corso.
#
# Messaggio badge -> dongle (interi little endian):
#   0  'P' 'R'          marcatore di inizio
#   2  versione (2)
#   3  tipo             1 = MACRO, 2 = ANNULLA
#   4  contatore u32    deve crescere sempre all'interno della sessione
#   8  lunghezza u16    dei dati (max MAX_PAYLOAD)
#   10 dati             MACRO: passi (vedi sotto), ANNULLA: vuoto
#   .. firma 16 byte    primi 16 byte di HMAC-SHA256(chiave, nonce || byte 2..10+lunghezza)
#   .. 'P' 'E'          marcatore di fine
#
# Passi di una MACRO:
#   1 mod tasto              premi e rilascia (mod = bit dei modificatori HID)
#   2 ms_lo ms_hi            pausa
#   3 n (mod tasto)*n        sequenza di tasti (testo)
#   4 uso_lo uso_hi          tasto multimediale (HID consumer control)
#
# Messaggi dongle -> badge (scritture sulla caratteristica stato):
#   1 pronta                 USB del PC: 1 = tastiera pronta
#   2 versione nonce(8) impronta(4)
#                            inizio sessione; impronta = SHA-256(chiave)[0:4]
#   3 contatore(u32) esito   esito di un messaggio (codici ESITO_*)

import hashlib

VERSIONE = 2

TIPO_MACRO = 1
TIPO_ANNULLA = 2

PASSO_TASTO = 1
PASSO_PAUSA = 2
PASSO_TASTI = 3
PASSO_MEDIA = 4

MAX_PAYLOAD = 6000
FIRMA_LEN = 16
INIZIO = 0x80

ST_USB = 1
ST_HELLO = 2
ST_ESITO = 3

ESITO_FATTO = 0x00
ESITO_IN_CORSO = 0x01
ESITO_ANNULLATO = 0x02
ESITO_FORMATO = 0x10
ESITO_FIRMA = 0x11
ESITO_RIPETUTO = 0x12
ESITO_TROPPO_LUNGO = 0x13
ESITO_OCCUPATO = 0x14
ESITO_USB = 0x15
ESITO_PASSO = 0x16
ESITO_NO_SESSIONE = 0x17

ESITO_TESTO = {
    ESITO_FATTO: "Fatto",
    ESITO_IN_CORSO: "In corso...",
    ESITO_ANNULLATO: "Annullato",
    ESITO_FORMATO: "Messaggio non valido",
    ESITO_FIRMA: "Firma non valida",
    ESITO_RIPETUTO: "Messaggio ripetuto",
    ESITO_TROPPO_LUNGO: "Comando troppo lungo",
    ESITO_OCCUPATO: "Dongle occupato",
    ESITO_USB: "USB del PC non pronta",
    ESITO_PASSO: "Comando non valido",
    ESITO_NO_SESSIONE: "Sessione non avviata",
}


def sha256(data):
    return hashlib.sha256(data).digest()


def hmac_sha256(key, msg):
    if len(key) > 64:
        key = sha256(key)
    key = key + bytes(64 - len(key))
    inner = sha256(bytes([b ^ 0x36 for b in key]) + msg)
    return sha256(bytes([b ^ 0x5C for b in key]) + inner)


def impronta(chiave):
    return sha256(chiave)[:4]


def leggi_chiave(testo):
    # 64 cifre esadecimali, spazi e righe ignorati
    h = "".join(testo.split())
    if len(h) != 64:
        raise ValueError("la chiave deve avere 64 cifre esadecimali")
    return bytes([int(h[i:i + 2], 16) for i in range(0, 64, 2)])


def _u16(v):
    return bytes((v & 0xFF, (v >> 8) & 0xFF))


def _u32(v):
    return bytes((v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF))


def _le(b):
    v = 0
    for i, x in enumerate(b):
        v |= x << (8 * i)
    return v


class Sessione:
    def __init__(self, chiave):
        self.chiave = chiave
        self.impronta = impronta(chiave)
        self.nonce = None
        self.contatore = 0

    def avvia(self, nonce):
        self.nonce = bytes(nonce)
        self.contatore = 0

    def attiva(self):
        return self.nonce is not None

    def messaggio(self, tipo, dati=b""):
        if self.nonce is None:
            raise ValueError("sessione non avviata")
        if len(dati) > MAX_PAYLOAD:
            raise ValueError("dati troppo lunghi")
        self.contatore += 1
        corpo = bytes((VERSIONE, tipo)) + _u32(self.contatore) + _u16(len(dati)) + bytes(dati)
        firma = hmac_sha256(self.chiave, self.nonce + corpo)[:FIRMA_LEN]
        return b"PR" + corpo + firma + b"PE"


def pezzi(messaggio, dimensione):
    # dimensione = byte utili per notify (MTU - 3); 1 byte va all'indice
    utili = dimensione - 1
    out = []
    i = 0
    for pos in range(0, len(messaggio), utili):
        testa = (i & 0x7F) | (INIZIO if pos == 0 else 0)
        out.append(bytes((testa,)) + messaggio[pos:pos + utili])
        i += 1
    return out


def leggi_stato(valore):
    # -> (ST_USB, pronta) | (ST_HELLO, versione, nonce, impronta)
    #    | (ST_ESITO, contatore, esito) | None se non riconosciuto
    if not valore:
        return None
    t = valore[0]
    if t == ST_USB and len(valore) >= 2:
        return (ST_USB, valore[1] == 1)
    if t == ST_HELLO and len(valore) >= 14:
        return (ST_HELLO, valore[1], bytes(valore[2:10]), bytes(valore[10:14]))
    if t == ST_ESITO and len(valore) >= 6:
        return (ST_ESITO, _le(valore[1:5]), valore[5])
    return None


# --- costruzione dei passi -------------------------------------------------

def passo_tasto(mod, tasto):
    return bytes((PASSO_TASTO, mod, tasto))


def passo_pausa(ms):
    ms = max(0, min(60000, int(ms)))
    return bytes((PASSO_PAUSA,)) + _u16(ms)


def passi_tasti(coppie):
    out = b""
    for i in range(0, len(coppie), 255):
        blocco = coppie[i:i + 255]
        out += bytes((PASSO_TASTI, len(blocco)))
        for mod, tasto in blocco:
            out += bytes((mod, tasto))
    return out


def passo_media(uso):
    return bytes((PASSO_MEDIA,)) + _u16(uso)
