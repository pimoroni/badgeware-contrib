# ui.py - colori e pezzi grafici comuni di wifi_config (HIRES 320x240, font.sins).
# Palette di apps/claude_monitor, cosi' le app hanno lo stesso aspetto.

W, H = 320, 240

BG = color.rgb(20, 30, 45)
PANEL = color.rgb(31, 53, 82)
TXT = color.rgb(245, 247, 250)
DIM = color.rgb(150, 165, 188)
ACC = color.rgb(90, 200, 220)
SEL = color.rgb(242, 169, 59)
SEL_TXT = color.rgb(20, 30, 45)
OK = color.rgb(90, 200, 120)
ERR = color.rgb(230, 60, 46)
KEY = color.rgb(44, 66, 98)
KEY_OK = color.rgb(40, 110, 70)
KEY_ANNULLA = color.rgb(110, 50, 50)
TRACCIA = color.rgb(58, 70, 88)

RIGHE_LISTA = 7


def larghezza(testo):
    return screen.measure_text(testo)[0]


def tronca(testo, max_w):
    """Accorcia con "..." finche' il testo sta in max_w pixel (SSID fino a 32 car.)."""
    if larghezza(testo) <= max_w:
        return testo
    while testo and larghezza(testo + "...") > max_w:
        testo = testo[:-1]
    return testo + "..."


def sfondo():
    screen.pen = BG
    screen.clear()


def titolo(testo, destra=None):
    screen.pen = PANEL
    screen.shape(shape.rounded_rectangle(8, 6, W - 16, 24, 8))
    screen.pen = TXT
    screen.text(testo, 16, 11)
    if destra:
        screen.pen = DIM
        screen.text(destra, W - 16 - larghezza(destra), 11)


def piede(testo):
    screen.pen = DIM
    screen.text(testo, (W - larghezza(testo)) // 2, H - 16)


def centrato(testo, y, colore=None):
    screen.pen = TXT if colore is None else colore
    screen.text(testo, (W - larghezza(testo)) // 2, y)


def pannello(x, y, w, h, r=10):
    screen.pen = PANEL
    screen.shape(shape.rounded_rectangle(x, y, w, h, r))


def menu(y, voci, sel, h=22):
    for i, voce in enumerate(voci):
        yy = y + i * (h + 4)
        if i == sel:
            screen.pen = SEL
            screen.shape(shape.rounded_rectangle(10, yy, W - 20, h, 6))
            screen.pen = SEL_TXT
        else:
            screen.pen = TXT
        screen.text(voce, 18, yy + (h - 12) // 2 + 1)


def pulsanti(y, etichette, sel, larg=90, passo=110):
    x0 = (W - (passo * (len(etichette) - 1) + larg)) // 2
    for i, e in enumerate(etichette):
        x = x0 + i * passo
        screen.pen = SEL if i == sel else KEY
        screen.shape(shape.rounded_rectangle(x, y, larg, 22, 6))
        screen.pen = SEL_TXT if i == sel else TXT
        screen.text(e, x + (larg - larghezza(e)) // 2, y + 5)


def segnale(x, y, livello):
    for i in range(4):
        h = 3 + i * 3
        screen.pen = ACC if i < livello else TRACCIA
        screen.shape(shape.rectangle(x + i * 4, y + 12 - h, 3, h))


def lucchetto(x, y, colore):
    screen.pen = colore
    screen.shape(shape.rectangle(x, y + 5, 9, 7))
    screen.shape(shape.arc(x + 4.5, y + 5, 2, 3.5, -90, 90))


def stella(x, y, colore):
    screen.pen = colore
    screen.shape(shape.star(x + 5, y + 6, 5, 6, 2.5))


def pallino(x, y, colore):
    screen.pen = colore
    screen.shape(shape.circle(x, y, 7))


def spinner(cx, cy, ora):
    a = (ora // 4) % 360
    screen.pen = TRACCIA
    screen.shape(shape.arc(cx, cy, 10, 14, 0, 360))
    screen.pen = ACC
    screen.shape(shape.arc(cx, cy, 10, 14, a, a + 100))


def finestra(sel, n, righe=RIGHE_LISTA):
    """Prima riga visibile di una lista lunga n con la selezione sempre a vista."""
    if n <= righe:
        return 0
    return max(0, min(sel - righe // 2, n - righe))


def riga_lista(y, sel):
    if sel:
        screen.pen = SEL
        screen.shape(shape.rounded_rectangle(8, y, W - 16, 22, 6))
    return SEL_TXT if sel else TXT


def scritta_destra(testo, y, colore, margine=18):
    screen.pen = colore
    screen.text(testo, W - margine - larghezza(testo), y)
