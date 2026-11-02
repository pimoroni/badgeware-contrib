# Lettura di comandi.json e traduzione in passi per il dongle.
#
# Nessuna dipendenza dalle API Badgeware (gira anche in CPython per i test).
# Tutta la conoscenza della tastiera sta qui: il dongle preme solo i codici
# HID ricevuti, quindi per cambiare layout o aggiungere nomi di tasti basta
# modificare questo file, senza ricaricare il firmware del dongle.
#
# Formato del file (vedi comandi.json):
#   {"gruppi": [{"nome": "...", "comandi": [ {comando}, ... ]}, ...]}
# Ogni comando ha "nome" e poi:
#   "url": "https://..."       apre l'indirizzo (Win+R, indirizzo, Invio)
#   "apri": "notepad"          avvia un programma (Win+R, nome, Invio),
#   "attesa": 1000               poi aspetta "attesa" ms (default 1000)
#   "testo": "riga 1\nriga 2"  scrive il testo
#   "tasti": "CTRL+C CTRL+V"   combinazioni separate da spazi
# eseguiti in quest'ordine (url, apri, testo, tasti), oppure in alternativa:
#   "passi": [["tasti","WIN+R"], ["pausa",400], ["testo","calc"], ["tasti","INVIO"]]
#   (tipi di passo: tasti, testo, pausa, url, apri)

import json

import protocollo as P

CTRL = 0x01
SHIFT = 0x02
ALT = 0x04
WIN = 0x08
ALTGR = 0x40

MODIFICATORI = {
    "CTRL": CTRL, "CONTROL": CTRL,
    "SHIFT": SHIFT, "MAIUSC": SHIFT,
    "ALT": ALT,
    "WIN": WIN, "GUI": WIN,
    "ALTGR": ALTGR,
}

TASTI_NOMINATI = {
    "INVIO": 0x28, "ENTER": 0x28,
    "ESC": 0x29,
    "BACKSPACE": 0x2A,
    "TAB": 0x2B,
    "SPAZIO": 0x2C, "SPACE": 0x2C,
    "STAMP": 0x46, "PRINTSCREEN": 0x46,
    "INS": 0x49, "INSERT": 0x49,
    "INIZIO": 0x4A, "HOME": 0x4A,
    "PAGSU": 0x4B, "PGUP": 0x4B,
    "CANC": 0x4C, "DEL": 0x4C, "DELETE": 0x4C,
    "FINE": 0x4D, "END": 0x4D,
    "PAGGIU": 0x4E, "PGDN": 0x4E,
    "DESTRA": 0x4F, "RIGHT": 0x4F,
    "SINISTRA": 0x50, "LEFT": 0x50,
    "GIU": 0x51, "DOWN": 0x51,
    "SU": 0x52, "UP": 0x52,
    "MENU": 0x65,
    "PIU": 0x30,  # il tasto "+" (non scrivibile dentro una combinazione)
}
for _n in range(1, 13):
    TASTI_NOMINATI["F%d" % _n] = 0x3A + _n - 1

TASTI_MEDIA = {
    "VOLSU": 0xE9, "VOLGIU": 0xEA, "MUTO": 0xE2,
    "PLAY": 0xCD, "TRACCIASUCC": 0xB5, "TRACCIAPREC": 0xB6,
}


def _layout_italiano():
    m = {}
    for i in range(26):
        m[chr(ord("a") + i)] = (0, 0x04 + i)
        m[chr(ord("A") + i)] = (SHIFT, 0x04 + i)
    cifre = "1234567890"
    shift_cifre = '!"£$%&/()='
    for i in range(10):
        m[cifre[i]] = (0, 0x1E + i)
        m[shift_cifre[i]] = (SHIFT, 0x1E + i)
    # (tasto HID, normale, shift, altgr, altgr+shift) nella posizione italiana
    tabella = (
        (0x2D, "'", "?", None, None),
        (0x2E, "ì", "^", None, None),
        (0x2F, "è", "é", "[", "{"),
        (0x30, "+", "*", "]", "}"),
        (0x33, "ò", "ç", "@", None),
        (0x34, "à", "°", "#", None),
        (0x31, "ù", "§", None, None),
        (0x35, "\\", "|", None, None),
        (0x64, "<", ">", None, None),
        (0x36, ",", ";", None, None),
        (0x37, ".", ":", None, None),
        (0x38, "-", "_", None, None),
    )
    for tasto, n, s, ag, ags in tabella:
        m[n] = (0, tasto)
        m[s] = (SHIFT, tasto)
        if ag:
            m[ag] = (ALTGR, tasto)
        if ags:
            m[ags] = (ALTGR | SHIFT, tasto)
    m["€"] = (ALTGR, 0x08)
    m[" "] = (0, 0x2C)
    m["\n"] = (0, 0x28)
    m["\t"] = (0, 0x2B)
    return m


LAYOUT = _layout_italiano()


class ErroreComando(Exception):
    pass


def coppie_testo(testo):
    out = []
    for c in testo:
        if c == "\r":
            continue
        k = LAYOUT.get(c)
        if k is None:
            raise ErroreComando("carattere non scrivibile: %s" % c)
        out.append(k)
    return out


def _combinazione(token):
    # -> passo (bytes) per una combinazione tipo "CTRL+SHIFT+T"
    parti = token.split("+")
    if any(p == "" for p in parti):
        raise ErroreComando("combinazione non valida: %s" % token)
    mods, ultimo = parti[:-1], parti[-1]
    mod = 0
    for nome in mods:
        v = MODIFICATORI.get(nome.upper())
        if v is None:
            raise ErroreComando("modificatore sconosciuto: %s" % nome)
        mod |= v
    nome = ultimo.upper()
    if nome in TASTI_MEDIA:
        if mod:
            raise ErroreComando("%s non va con i modificatori" % nome)
        return P.passo_media(TASTI_MEDIA[nome])
    if nome in TASTI_NOMINATI:
        return P.passo_tasto(mod, TASTI_NOMINATI[nome])
    if nome in MODIFICATORI and not mods:
        # tasto modificatore da solo, es. "WIN" per aprire Start
        return P.passo_tasto(MODIFICATORI[nome], 0)
    if len(ultimo) == 1:
        k = LAYOUT.get(ultimo.lower() if ultimo.isalpha() else ultimo)
        if k is not None:
            return P.passo_tasto(mod | k[0], k[1])
    raise ErroreComando("tasto sconosciuto: %s" % ultimo)


def passi_combinazioni(testo):
    out = b""
    for token in testo.split():
        out += _combinazione(token)
    if not out:
        raise ErroreComando("nessun tasto indicato")
    return out


def _esegui_da_win_r(testo, attesa):
    return (passi_combinazioni("WIN+R") + P.passo_pausa(600)
            + P.passi_tasti(coppie_testo(testo)) + passi_combinazioni("INVIO")
            + P.passo_pausa(attesa))


def _stringa(cmd, chiave):
    v = cmd[chiave]
    if not isinstance(v, str) or not v:
        raise ErroreComando("'%s' deve essere un testo" % chiave)
    return v


def compila(cmd):
    if not isinstance(cmd, dict):
        raise ErroreComando("il comando deve essere un oggetto {...}")
    noti = ("nome", "url", "apri", "attesa", "testo", "tasti", "passi")
    for k in cmd:
        if k not in noti:
            raise ErroreComando("campo sconosciuto: %s" % k)
    if "passi" in cmd:
        if len(cmd) > 2:
            raise ErroreComando("'passi' non va insieme ad altri campi")
        return _compila_passi(cmd["passi"])
    out = b""
    if "url" in cmd:
        out += _esegui_da_win_r(_stringa(cmd, "url"), 300)
    if "apri" in cmd:
        attesa = cmd.get("attesa", 1000)
        if not isinstance(attesa, int):
            raise ErroreComando("'attesa' deve essere un numero di ms")
        out += _esegui_da_win_r(_stringa(cmd, "apri"), attesa)
    if "testo" in cmd:
        out += P.passi_tasti(coppie_testo(_stringa(cmd, "testo")))
    if "tasti" in cmd:
        out += passi_combinazioni(_stringa(cmd, "tasti"))
    if not out:
        raise ErroreComando("manca url, apri, testo, tasti o passi")
    return out


def _compila_passi(passi):
    if not isinstance(passi, list) or not passi:
        raise ErroreComando("'passi' deve essere una lista non vuota")
    out = b""
    for n, p in enumerate(passi, 1):
        if not isinstance(p, list) or len(p) != 2:
            raise ErroreComando("passo %d: serve [tipo, valore]" % n)
        tipo, valore = p
        if tipo == "pausa":
            if not isinstance(valore, int):
                raise ErroreComando("passo %d: la pausa e' in ms" % n)
            out += P.passo_pausa(valore)
            continue
        if not isinstance(valore, str) or not valore:
            raise ErroreComando("passo %d: valore mancante" % n)
        if tipo == "tasti":
            out += passi_combinazioni(valore)
        elif tipo == "testo":
            out += P.passi_tasti(coppie_testo(valore))
        elif tipo == "url":
            out += _esegui_da_win_r(valore, 300)
        elif tipo == "apri":
            out += _esegui_da_win_r(valore, 1000)
        else:
            raise ErroreComando("passo %d: tipo sconosciuto %s" % (n, tipo))
    return out


# comandi della modalita' presentazione
PRESENTAZIONE = {
    "avanti": passi_combinazioni("PAGGIU"),
    "indietro": passi_combinazioni("PAGSU"),
    "avvio": passi_combinazioni("F5"),
    "avvio_qui": passi_combinazioni("SHIFT+F5"),
    "fine": passi_combinazioni("ESC"),
    "nero": passi_combinazioni("b"),
}


def descrizione(cmd):
    # riga di aiuto mostrata sotto la voce selezionata
    if not isinstance(cmd, dict):
        return ""
    if isinstance(cmd.get("url"), str):
        return "Apre " + cmd["url"]
    if isinstance(cmd.get("apri"), str):
        return "Avvia " + cmd["apri"] + (" e scrive un testo" if "testo" in cmd else "")
    if isinstance(cmd.get("tasti"), str):
        return "Tasti: " + cmd["tasti"]
    if isinstance(cmd.get("testo"), str):
        t = cmd["testo"].replace("\n", " ")
        return "Scrive: " + (t if len(t) <= 30 else t[:30] + "...")
    if isinstance(cmd.get("passi"), list):
        return "Macro di %d passi" % len(cmd["passi"])
    return ""


def carica(testo):
    # -> (gruppi, errore). gruppi: [{"nome", "comandi": [{"nome", "dati", "errore", "info"}]}]
    # Prima il controllo severo: il json di MicroPython accetta anche file
    # sbagliati (es. virgole mancanti) che altri programmi rifiuterebbero.
    err = errore_json(testo)
    if err:
        return [], err
    try:
        dati = json.loads(testo)
    except ValueError:
        return [], "JSON non valido"
    if not isinstance(dati, dict) or not isinstance(dati.get("gruppi"), list):
        return [], 'manca la lista "gruppi"'
    gruppi = []
    for gi, g in enumerate(dati["gruppi"], 1):
        if not isinstance(g, dict) or not isinstance(g.get("comandi"), list):
            return [], 'gruppo %d: manca la lista "comandi"' % gi
        nome_g = g.get("nome") if isinstance(g.get("nome"), str) else "Gruppo %d" % gi
        voci = []
        for ci, c in enumerate(g["comandi"], 1):
            nome = c.get("nome") if isinstance(c, dict) and isinstance(c.get("nome"), str) else "Comando %d" % ci
            try:
                d = compila(c)
                if len(d) > P.MAX_PAYLOAD:
                    raise ErroreComando("troppo lungo")
                voci.append({"nome": nome, "dati": d, "errore": None, "info": descrizione(c)})
            except ErroreComando as e:
                voci.append({"nome": nome, "dati": None, "errore": str(e), "info": ""})
        gruppi.append({"nome": nome_g, "comandi": voci})
    if not gruppi:
        return [], "nessun gruppo definito"
    return gruppi, None


# --- posizione dell'errore JSON --------------------------------------------
# Il json di MicroPython e' tollerante e non dice dove sta l'errore: questo
# piccolo parser controlla il file in modo severo e ne indica la riga.

class _Fine(Exception):
    def __init__(self, pos, msg):
        self.pos = pos
        self.msg = msg


def errore_json(testo):
    # -> None se il JSON e' valido, altrimenti "JSON, riga N: motivo"
    p = _ParserJson(testo)
    try:
        p.valore()
        p.spazi()
        if p.i < len(testo):
            raise _Fine(p.i, "testo dopo la fine")
        return None
    except _Fine as e:
        riga = testo[:e.pos].count("\n") + 1
        return "JSON, riga %d: %s" % (riga, e.msg)


class _ParserJson:
    def __init__(self, t):
        self.t = t
        self.i = 0

    def spazi(self):
        while self.i < len(self.t) and self.t[self.i] in " \t\r\n":
            self.i += 1

    def car(self):
        self.spazi()
        if self.i >= len(self.t):
            raise _Fine(self.i, "file troncato")
        return self.t[self.i]

    def atteso(self, c):
        if self.car() != c:
            raise _Fine(self.i, "atteso '%s'" % c)
        self.i += 1

    def valore(self):
        c = self.car()
        if c == "{":
            self.i += 1
            if self.car() == "}":
                self.i += 1
                return
            while True:
                self.stringa()
                self.atteso(":")
                self.valore()
                c = self.car()
                if c == ",":
                    self.i += 1
                    if self.car() == "}":
                        raise _Fine(self.i, "virgola di troppo")
                elif c == "}":
                    self.i += 1
                    return
                else:
                    raise _Fine(self.i, "manca una virgola o '}'")
        elif c == "[":
            self.i += 1
            if self.car() == "]":
                self.i += 1
                return
            while True:
                self.valore()
                c = self.car()
                if c == ",":
                    self.i += 1
                    if self.car() == "]":
                        raise _Fine(self.i, "virgola di troppo")
                elif c == "]":
                    self.i += 1
                    return
                else:
                    raise _Fine(self.i, "manca una virgola o ']'")
        elif c == '"':
            self.stringa()
        else:
            inizio = self.i
            while self.i < len(self.t) and self.t[self.i] not in " \t\r\n,]}":
                self.i += 1
            parola = self.t[inizio:self.i]
            if parola in ("true", "false", "null"):
                return
            try:
                float(parola)
            except ValueError:
                raise _Fine(inizio, 'valore non valido (testi tra "virgolette")')  # noqa: B904

    def stringa(self):
        if self.car() != '"':
            raise _Fine(self.i, 'atteso un testo tra "virgolette"')
        self.i += 1
        while self.i < len(self.t):
            c = self.t[self.i]
            if c == "\\":
                self.i += 2
                continue
            if c == "\n":
                raise _Fine(self.i, "testo non chiuso (per andare a capo usa \\n)")
            self.i += 1
            if c == '"':
                return
        raise _Fine(self.i, "testo non chiuso")


# --- testo a schermo -------------------------------------------------------
# I font ROM sono ASCII: le lettere accentate si mostrano come "e'".

_ACCENTI = {"à": "a'", "è": "e'", "é": "e'", "ì": "i'", "ò": "o'", "ù": "u'",
            "À": "A'", "È": "E'", "É": "E'", "Ì": "I'", "Ò": "O'", "Ù": "U'"}


def per_schermo(s):
    out = ""
    for c in s:
        if c in _ACCENTI:
            out += _ACCENTI[c]
        elif " " <= c <= "~":
            out += c
        else:
            out += "?"
    return out
