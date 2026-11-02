# tastiera.py - tastiera virtuale a griglia per la password WiFi.
#
# A = sinistra, C = destra, SU/GIU = riga, B = preme il tasto evidenziato.
# 7 righe di caratteri (13 colonne) + una riga di tasti speciali: insieme
# coprono tutti i 95 caratteri ASCII stampabili. Movimento circolare; tra la
# riga 6 e quella speciale si va al tasto piu' vicino in orizzontale.

RIGHE = [
    "abcdefghijklm",
    "nopqrstuvwxyz",
    "ABCDEFGHIJKLM",
    "NOPQRSTUVWXYZ",
    "0123456789.-_",
    "!@#$%&*?+=/:;",
    "()[]{}<>,'\"~^",
]
SPECIALI = ["spazio", "\\", "|", "`", "Canc", "OK", "Annulla"]
_TESTO_SPECIALE = {"spazio": " ", "\\": "\\", "|": "|", "`": "`"}

MIN_LEN = 8
MAX_LEN = 63

# geometria (HIRES 320x240), usata anche per scegliere il tasto piu' vicino
W = 320
CELLA_W, CELLA_H = 23, 17
GRIGLIA_X = (W - 13 * CELLA_W) // 2
GRIGLIA_Y = 80
SPECIALI_W = [56, 22, 22, 22, 44, 40, 68]
_GAP = 2
SPECIALI_X = []
_x = (W - sum(SPECIALI_W) - _GAP * (len(SPECIALI_W) - 1)) // 2
for _w in SPECIALI_W:
    SPECIALI_X.append(_x)
    _x += _w + _GAP
RIGA_SPECIALE = len(RIGHE)


def _centro(riga, col):
    if riga == RIGA_SPECIALE:
        return SPECIALI_X[col] + SPECIALI_W[col] / 2
    return GRIGLIA_X + col * CELLA_W + CELLA_W / 2


def _piu_vicino(riga, x):
    n = len(SPECIALI) if riga == RIGA_SPECIALE else len(RIGHE[riga])
    return min(range(n), key=lambda c: abs(_centro(riga, c) - x))


class Tastiera:
    def __init__(self, testo=""):
        self.testo = testo
        self.riga = 0
        self.col = 0

    def muovi(self, dr, dc):
        if dc:
            n = len(SPECIALI) if self.riga == RIGA_SPECIALE else len(RIGHE[self.riga])
            self.col = (self.col + dc) % n
        if dr:
            x = _centro(self.riga, self.col)
            nuova = (self.riga + dr) % (RIGA_SPECIALE + 1)
            if (self.riga == RIGA_SPECIALE) != (nuova == RIGA_SPECIALE):
                self.col = _piu_vicino(nuova, x)
            self.riga = nuova

    def tasto(self):
        if self.riga == RIGA_SPECIALE:
            return SPECIALI[self.col]
        return RIGHE[self.riga][self.col]

    def premi(self):
        """None dopo aver scritto/cancellato, "ok", "corta" o "annulla"."""
        t = self.tasto()
        if self.riga == RIGA_SPECIALE and t not in _TESTO_SPECIALE:
            if t == "Canc":
                self.testo = self.testo[:-1]
                return None
            if t == "OK":
                return "corta" if len(self.testo) < MIN_LEN else "ok"
            return "annulla"
        if len(self.testo) < MAX_LEN:
            self.testo += _TESTO_SPECIALE.get(t, t)
        return None

    def disegna(self, ssid, messaggio=None, colore=None):
        import ui
        scr = screen  # noqa: F821 - builtin Badgeware
        ui.titolo("Password", ui.tronca(ssid, 190))

        # campo password in chiaro, si mostra la parte finale se non ci sta
        scr.pen = ui.PANEL
        scr.shape(shape.rounded_rectangle(10, 36, W - 20, 22, 6))  # noqa: F821
        conteggio = "{} car.".format(len(self.testo))
        spazio = W - 36 - ui.larghezza(conteggio) - 12
        visibile = self.testo
        while visibile and ui.larghezza(visibile + "_") > spazio:
            visibile = visibile[1:]
        scr.pen = ui.TXT
        scr.text(visibile, 18, 41)
        scr.pen = ui.ACC
        scr.shape(shape.rectangle(18 + ui.larghezza(visibile) + 1, 51, 7, 2))  # noqa: F821
        scr.pen = ui.DIM
        scr.text(conteggio, W - 18 - ui.larghezza(conteggio), 41)

        if messaggio:
            scr.pen = colore if colore is not None else ui.ERR
            scr.text(messaggio, 12, 63)
        else:
            scr.pen = ui.DIM
            scr.text("A/C sx-dx  SU/GIU riga  B scrivi", 12, 63)

        for r, caratteri in enumerate(RIGHE):
            for c, ch in enumerate(caratteri):
                x = GRIGLIA_X + c * CELLA_W
                y = GRIGLIA_Y + r * CELLA_H
                sel = (r, c) == (self.riga, self.col)
                scr.pen = ui.SEL if sel else ui.KEY
                scr.shape(shape.rounded_rectangle(x + 1, y + 1, CELLA_W - 2, CELLA_H - 2, 3))  # noqa: F821
                scr.pen = ui.SEL_TXT if sel else ui.TXT
                scr.text(ch, x + (CELLA_W - ui.larghezza(ch)) // 2, y + 3)

        y = GRIGLIA_Y + RIGA_SPECIALE * CELLA_H + 2
        for i, etichetta in enumerate(SPECIALI):
            sel = self.riga == RIGA_SPECIALE and self.col == i
            base = ui.KEY
            if etichetta == "OK":
                base = ui.KEY_OK
            elif etichetta == "Annulla":
                base = ui.KEY_ANNULLA
            scr.pen = ui.SEL if sel else base
            scr.shape(shape.rounded_rectangle(SPECIALI_X[i], y, SPECIALI_W[i], CELLA_H + 1, 4))  # noqa: F821
            scr.pen = ui.SEL_TXT if sel else ui.TXT
            scr.text(etichetta, SPECIALI_X[i] + (SPECIALI_W[i] - ui.larghezza(etichetta)) // 2, y + 4)


class Ripetitore:
    """Trasforma pressioni e tasti tenuti in eventi: il tasto appena premuto
    scatta subito; se resta giu', dopo `ritardo` ms riscatta ogni `passo` ms
    (solo per i tasti in `ripetibili`)."""

    def __init__(self, ripetibili, ritardo=400, passo=100):
        self.ripetibili = ripetibili
        self.ritardo = ritardo
        self.passo = passo
        self._prossimo = {}

    def tasti(self, premuti, tenuti, ora, solo=None):
        """`solo` limita la ripetizione a quei tasti (per schermata): sulle
        conferme A/C non devono alternare la scelta finche' restano giu'."""
        eventi = list(premuti)
        for k in list(self._prossimo):
            if k not in tenuti:
                del self._prossimo[k]
        for k in premuti:
            if k in self.ripetibili:
                self._prossimo[k] = ora + self.ritardo
        for k, quando in list(self._prossimo.items()):
            if solo is not None and k not in solo:
                continue
            if k not in premuti and ora >= quando:
                eventi.append(k)
                self._prossimo[k] = ora + self.passo
        return eventi
