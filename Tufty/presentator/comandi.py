# Lettura di comandi.json e traduzione in passi per il dongle.
#
# Nessuna dipendenza dalle API Badgeware (gira anche in CPython per i test).
# Tutta la conoscenza della tastiera sta qui: il dongle preme solo i codici
# HID ricevuti, quindi per cambiare layout o aggiungere nomi di tasti basta
# modificare questo file, senza ricaricare il firmware del dongle.
#
# Layout della tastiera del PC (impostazione dell'app): "it", "us", "uk"
# (US semplice, non US-International: quello ha tasti morti su ' " ` ~ ^).
#
# Formato del file (vedi comandi.example.json); ogni chiave si puo' scrivere
# in inglese o in italiano:
#   {"groups": [{"name": "...", "commands": [ {comando}, ... ]}, ...]}
#   ("gruppi", "nome", "comandi")
# Ogni comando ha "name" e poi:
#   "url": "https://..."        apre l'indirizzo (Win+R, indirizzo, Invio)
#   "open": "notepad"           avvia un programma (Win+R, nome, Invio),
#   "wait": 1000                  poi aspetta "wait" ms (default 1000)
#   "text": "line 1\nline 2"    scrive il testo
#   "keys": "CTRL+C CTRL+V"     combinazioni separate da spazi
#   ("apri", "attesa", "testo", "tasti")
# eseguiti in quest'ordine (url, open, text, keys), oppure in alternativa:
#   "steps": [["keys","WIN+R"], ["pause",400], ["text","calc"], ["keys","ENTER"]]
#   ("passi"; tipi di passo: keys/tasti, text/testo, pause/pausa, url, open/apri)

import json

import lingua as L
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
}
for _n in range(1, 13):
    TASTI_NOMINATI["F%d" % _n] = 0x3A + _n - 1

# il tasto "+" non si puo' scrivere dentro una combinazione: lo si indica per
# nome e la sua posizione dipende dal layout
TASTO_PIU = ("PIU", "PLUS")

TASTI_MEDIA = {
    "VOLSU": 0xE9, "VOLUP": 0xE9,
    "VOLGIU": 0xEA, "VOLDOWN": 0xEA,
    "MUTO": 0xE2, "MUTE": 0xE2,
    "PLAY": 0xCD,
    "TRACCIASUCC": 0xB5, "NEXTTRACK": 0xB5,
    "TRACCIAPREC": 0xB6, "PREVTRACK": 0xB6,
}

# Tabelle dei layout: (tasto HID, normale, shift, altgr, altgr+shift) per i
# tasti che cambiano tra un layout e l'altro. Lettere, spazio, Invio e Tab
# sono uguali ovunque; le cifre hanno simboli diversi con shift.
_TABELLE = {
    "it": ('!"£$%&/()=', (
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
        (0x08, None, None, "€", None),
    )),
    "us": ("!@#$%^&*()", (
        (0x2D, "-", "_", None, None),
        (0x2E, "=", "+", None, None),
        (0x2F, "[", "{", None, None),
        (0x30, "]", "}", None, None),
        (0x31, "\\", "|", None, None),
        (0x33, ";", ":", None, None),
        (0x34, "'", '"', None, None),
        (0x35, "`", "~", None, None),
        (0x36, ",", "<", None, None),
        (0x37, ".", ">", None, None),
        (0x38, "/", "?", None, None),
    )),
    "uk": ('!"£$%^&*()', (
        (0x2D, "-", "_", None, None),
        (0x2E, "=", "+", None, None),
        (0x2F, "[", "{", None, None),
        (0x30, "]", "}", None, None),
        (0x32, "#", "~", None, None),
        (0x33, ";", ":", None, None),
        (0x34, "'", "@", None, None),
        (0x35, "`", "¬", "¦", None),
        (0x64, "\\", "|", None, None),
        (0x36, ",", "<", None, None),
        (0x37, ".", ">", None, None),
        (0x38, "/", "?", None, None),
        (0x21, None, None, "€", None),
        # AltGr + vocale = vocale con accento acuto (layout UK di Windows)
        (0x04, None, None, "á", "Á"),
        (0x08, None, None, "é", "É"),
        (0x0C, None, None, "í", "Í"),
        (0x12, None, None, "ó", "Ó"),
        (0x18, None, None, "ú", "Ú"),
    )),
}
LAYOUTS = ("it", "us", "uk")


def costruisci_layout(codice):
    shift_cifre, tabella = _TABELLE[codice]
    m = {}
    for i in range(26):
        m[chr(ord("a") + i)] = (0, 0x04 + i)
        m[chr(ord("A") + i)] = (SHIFT, 0x04 + i)
    cifre = "1234567890"
    for i in range(10):
        m[cifre[i]] = (0, 0x1E + i)
        m[shift_cifre[i]] = (SHIFT, 0x1E + i)
    for tasto, n, s, ag, ags in tabella:
        for c, mod in ((n, 0), (s, SHIFT), (ag, ALTGR), (ags, ALTGR | SHIFT)):
            if c:
                m[c] = (mod, tasto)
    m[" "] = (0, 0x2C)
    m["\n"] = (0, 0x28)
    m["\t"] = (0, 0x2B)
    return m


LAYOUT = {}
PRESENTAZIONE = {}


class ErroreComando(Exception):
    pass


def _errore(chiave, *args):
    return ErroreComando(L.t(chiave, *args))


def coppie_testo(testo):
    out = []
    for c in testo:
        if c == "\r":
            continue
        k = LAYOUT.get(c)
        if k is None:
            raise _errore("ce_char", c)
        out.append(k)
    return out


def _combinazione(token):
    # -> passo (bytes) per una combinazione tipo "CTRL+SHIFT+T"
    parti = token.split("+")
    if any(p == "" for p in parti):
        raise _errore("ce_combo", token)
    mods, ultimo = parti[:-1], parti[-1]
    mod = 0
    for nome in mods:
        v = MODIFICATORI.get(nome.upper())
        if v is None:
            raise _errore("ce_mod", nome)
        mod |= v
    nome = ultimo.upper()
    if nome in TASTI_MEDIA:
        if mod:
            raise _errore("ce_media_mod", nome)
        return P.passo_media(TASTI_MEDIA[nome])
    if nome in TASTI_NOMINATI:
        return P.passo_tasto(mod, TASTI_NOMINATI[nome])
    if nome in TASTO_PIU:
        k = LAYOUT["+"]
        return P.passo_tasto(mod | k[0], k[1])
    if nome in MODIFICATORI and not mods:
        # tasto modificatore da solo, es. "WIN" per aprire Start
        return P.passo_tasto(MODIFICATORI[nome], 0)
    if len(ultimo) == 1:
        k = LAYOUT.get(ultimo.lower() if ultimo.isalpha() else ultimo)
        if k is not None:
            return P.passo_tasto(mod | k[0], k[1])
    raise _errore("ce_key", ultimo)


def passi_combinazioni(testo):
    out = b""
    for token in testo.split():
        out += _combinazione(token)
    if not out:
        raise _errore("ce_nokeys")
    return out


def imposta_layout(codice):
    # -> codice effettivamente usato ("us" se sconosciuto)
    global LAYOUT, PRESENTAZIONE
    if codice not in _TABELLE:
        codice = "us"
    LAYOUT = costruisci_layout(codice)
    # comandi della modalita' presentazione (uguali in tutti i layout)
    PRESENTAZIONE = {
        "avanti": passi_combinazioni("PGDN"),
        "indietro": passi_combinazioni("PGUP"),
        "avvio": passi_combinazioni("F5"),
        "avvio_qui": passi_combinazioni("SHIFT+F5"),
        "fine": passi_combinazioni("ESC"),
        "nero": passi_combinazioni("b"),
    }
    return codice


imposta_layout("us")


def _esegui_da_win_r(testo, attesa):
    return (passi_combinazioni("WIN+R") + P.passo_pausa(600)
            + P.passi_tasti(coppie_testo(testo)) + passi_combinazioni("ENTER")
            + P.passo_pausa(attesa))


# chiavi del file in inglese -> nomi interni (italiani)
_ALIAS = {
    "groups": "gruppi", "commands": "comandi", "name": "nome", "open": "apri",
    "wait": "attesa", "text": "testo", "keys": "tasti", "steps": "passi",
    "pause": "pausa",
}


def _normalizza(d):
    # copia con le chiavi tradotte; per i messaggi resta il nome originale
    if not isinstance(d, dict):
        return d, {}
    out = {}
    originali = {}
    for k, v in d.items():
        interno = _ALIAS.get(k, k)
        out[interno] = v
        originali[interno] = k
    return out, originali


def _stringa(cmd, chiave, originali):
    v = cmd[chiave]
    if not isinstance(v, str) or not v:
        raise _errore("ce_text", originali.get(chiave, chiave))
    return v


def compila(cmd):
    if not isinstance(cmd, dict):
        raise _errore("ce_obj")
    cmd, originali = _normalizza(cmd)
    noti = ("nome", "url", "apri", "attesa", "testo", "tasti", "passi")
    for k in cmd:
        if k not in noti:
            raise _errore("ce_field", originali.get(k, k))
    if "passi" in cmd:
        if len(cmd) > 2:
            raise _errore("ce_steps_alone")
        return _compila_passi(cmd["passi"])
    out = b""
    if "url" in cmd:
        out += _esegui_da_win_r(_stringa(cmd, "url", originali), 300)
    if "apri" in cmd:
        attesa = cmd.get("attesa", 1000)
        if not isinstance(attesa, int):
            raise _errore("ce_wait")
        out += _esegui_da_win_r(_stringa(cmd, "apri", originali), attesa)
    if "testo" in cmd:
        out += P.passi_tasti(coppie_testo(_stringa(cmd, "testo", originali)))
    if "tasti" in cmd:
        out += passi_combinazioni(_stringa(cmd, "tasti", originali))
    if not out:
        raise _errore("ce_empty")
    return out


def _compila_passi(passi):
    if not isinstance(passi, list) or not passi:
        raise _errore("ce_steps_list")
    out = b""
    for n, p in enumerate(passi, 1):
        if not isinstance(p, list) or len(p) != 2:
            raise _errore("ce_step_pair", n)
        tipo, valore = p
        tipo = _ALIAS.get(tipo, tipo)
        if tipo == "pausa":
            if not isinstance(valore, int):
                raise _errore("ce_step_pause", n)
            out += P.passo_pausa(valore)
            continue
        if not isinstance(valore, str) or not valore:
            raise _errore("ce_step_value", n)
        if tipo == "tasti":
            out += passi_combinazioni(valore)
        elif tipo == "testo":
            out += P.passi_tasti(coppie_testo(valore))
        elif tipo == "url":
            out += _esegui_da_win_r(valore, 300)
        elif tipo == "apri":
            out += _esegui_da_win_r(valore, 1000)
        else:
            raise _errore("ce_step_type", n, p[0])
    return out


def descrizione(cmd):
    # riga di aiuto mostrata sotto la voce selezionata
    cmd, _ = _normalizza(cmd)
    if not isinstance(cmd, dict):
        return ""
    if isinstance(cmd.get("url"), str):
        return L.t("ds_url", cmd["url"])
    if isinstance(cmd.get("apri"), str):
        return L.t("ds_open_text" if "testo" in cmd else "ds_open", cmd["apri"])
    if isinstance(cmd.get("tasti"), str):
        return L.t("ds_keys", cmd["tasti"])
    if isinstance(cmd.get("testo"), str):
        t = cmd["testo"].replace("\n", " ")
        return L.t("ds_text", t if len(t) <= 30 else t[:30] + "...")
    if isinstance(cmd.get("passi"), list):
        return L.t("ds_steps", len(cmd["passi"]))
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
        return [], L.t("cj_invalid")
    dati, _ = _normalizza(dati)
    if not isinstance(dati, dict) or not isinstance(dati.get("gruppi"), list):
        return [], L.t("cj_no_groups")
    gruppi = []
    for gi, g in enumerate(dati["gruppi"], 1):
        g, _ = _normalizza(g)
        if not isinstance(g, dict) or not isinstance(g.get("comandi"), list):
            return [], L.t("cj_group_no_cmds", gi)
        nome_g = g.get("nome") if isinstance(g.get("nome"), str) else L.t("cj_group_name", gi)
        voci = []
        for ci, c in enumerate(g["comandi"], 1):
            cn, _ = _normalizza(c)
            nome = cn.get("nome") if isinstance(cn, dict) and isinstance(cn.get("nome"), str) else L.t("cj_cmd_name", ci)
            try:
                d = compila(c)
                if len(d) > P.MAX_PAYLOAD:
                    raise _errore("ce_too_long")
                voci.append({"nome": nome, "dati": d, "errore": None, "info": descrizione(c)})
            except ErroreComando as e:
                voci.append({"nome": nome, "dati": None, "errore": str(e), "info": ""})
        gruppi.append({"nome": nome_g, "comandi": voci})
    if not gruppi:
        return [], L.t("cj_no_group")
    return gruppi, None


# --- posizione dell'errore JSON --------------------------------------------
# Il json di MicroPython e' tollerante e non dice dove sta l'errore: questo
# piccolo parser controlla il file in modo severo e ne indica la riga.

class _Fine(Exception):
    def __init__(self, pos, chiave, *args):
        self.pos = pos
        self.msg = L.t(chiave, *args)


def errore_json(testo):
    # -> None se il JSON e' valido, altrimenti "JSON, riga N: motivo"
    p = _ParserJson(testo)
    try:
        p.valore()
        p.spazi()
        if p.i < len(testo):
            raise _Fine(p.i, "jp_after")
        return None
    except _Fine as e:
        riga = testo[:e.pos].count("\n") + 1
        return L.t("cj_line", riga, e.msg)


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
            raise _Fine(self.i, "jp_trunc")
        return self.t[self.i]

    def atteso(self, c):
        if self.car() != c:
            raise _Fine(self.i, "jp_expected", c)
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
                        raise _Fine(self.i, "jp_extra_comma")
                elif c == "}":
                    self.i += 1
                    return
                else:
                    raise _Fine(self.i, "jp_comma_brace")
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
                        raise _Fine(self.i, "jp_extra_comma")
                elif c == "]":
                    self.i += 1
                    return
                else:
                    raise _Fine(self.i, "jp_comma_bracket")
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
                raise _Fine(inizio, "jp_value")  # noqa: B904

    def stringa(self):
        if self.car() != '"':
            raise _Fine(self.i, "jp_string")
        self.i += 1
        while self.i < len(self.t):
            c = self.t[self.i]
            if c == "\\":
                self.i += 2
                continue
            if c == "\n":
                raise _Fine(self.i, "jp_unclosed_nl")
            self.i += 1
            if c == '"':
                return
        raise _Fine(self.i, "jp_unclosed")
