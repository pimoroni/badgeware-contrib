# Presentator - telecomando per presentazioni e lanciacomandi per il PC,
# basato sul Bluetooth LE del Tufty 2350.
#
# Perche' serve un dongle: il firmware ufficiale (MicroPython pimoroni
# bw-1.28.0-3 + BTstack) e' compilato senza MICROPY_PY_BLUETOOTH_ENABLE_
# PAIRING_BONDING e non conferma mai la richiesta "Just Works" di BTstack,
# quindi Windows non riesce ad abbinare il badge come tastiera BLE (HID over
# GATT richiede sempre l'abbinamento). Per non toccare il firmware ufficiale
# e non installare nulla sul PC, il badge espone un servizio GATT e un
# ESP32-S3 inserito in una porta USB del PC (../../presentator_dongle) si
# collega al badge e preme i tasti come una normale tastiera USB.
#
# Il badge traduce tutto in codici tasto HID (layout italiano, comandi.py) e
# firma ogni messaggio con la chiave in chiave.txt (protocollo.py): il dongle
# esegue solo messaggi firmati, nuovi e della sessione in corso.
#
# File dell'app:
#   comandi.json   voci del menu "Invia comandi" (modificabile in Disk Mode);
#                  se manca si usa comandi.example.json
#   chiave.txt     chiave segreta, generata da presentator_dongle/tools/genera_chiave.py
#
# Schermate e tasti (la legenda in basso li mostra sempre):
#   menu           SU/GIU sceglie, B apre
#   presentazione  C/GIU avanti, A/SU indietro, B nero; tenuti: SU avvia (F5),
#                  B avvia da qui (Maiusc+F5), GIU fine (Esc), A torna al menu
#   comandi        SU/GIU scorre, B apre/invia, A torna indietro o annulla
#   HOME           esce dall'app (riavvia il badge, gestito dal firmware)

import bluetooth
from micropython import const

import comandi as C
import protocollo as P

badge.mode(HIRES | VSYNC)
screen.antialias = image.X2

FONT_TESTO = font.nope        # 8 px, chiaro
FONT_TITOLO = font.yesterday  # 10 px, marcato
FONT_PICCOLO = font.sins      # 7 px: legenda e riga di stato
FH_PICCOLO = FONT_PICCOLO.height

# --- costanti -------------------------------------------------------------

_SVC_UUID = bluetooth.UUID("b3bb28a0-5c30-4245-9c7d-2ee9a9e560f9")
_CMD_UUID = bluetooth.UUID("ed860c12-e173-41b6-af88-c33fe321ca13")
_STATUS_UUID = bluetooth.UUID("1d2189ac-03a9-42f3-bd51-69a7747e0b4d")

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_MTU_EXCHANGED = const(21)

_FLAG_READ = const(0x0002)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

DEVICE_NAME = "Presentator"
ADV_INTERVAL_US = 100_000
PEZZI_PER_FRAME = 6
TIMEOUT_RISPOSTA_MS = 4000

LONG_PRESS_MS = 700
TOAST_MS = 1400
REPEAT_DELAY_MS = 400
REPEAT_MS = 110

BG_COLOR = color.rgb(18, 22, 34)
PANEL_COLOR = color.rgb(36, 46, 70)
SEL_COLOR = color.rgb(60, 78, 120)
TEXT_COLOR = color.rgb(240, 244, 250)
DIM_TEXT_COLOR = color.rgb(150, 162, 185)
OK_COLOR = color.rgb(70, 205, 120)
WAIT_COLOR = color.rgb(245, 170, 50)
ERR_COLOR = color.rgb(235, 80, 70)
ACCENT_COLOR = color.rgb(255, 120, 40)
CHIP_COLOR = color.rgb(255, 120, 40)
CHIP_TEXT = color.rgb(18, 22, 34)

W = screen.width
H = screen.height
HEADER_Y, HEADER_H = 4, 42
# legenda: righe da 3 tasti; la riga "tieni: ..." solo dove serve. La sua
# altezza dipende dalla schermata, il corpo occupa lo spazio che resta
# (LEGEND_Y e BODY_H ricalcolati a ogni frame in update()).
CHIP_H = FH_PICCOLO + 5
RIGA_LEGENDA = CHIP_H + FH_PICCOLO + 8
RIGA_LEGENDA_CORTA = CHIP_H + 6
BODY_Y = 50
LEGEND_Y = H - 40
BODY_H = LEGEND_Y - 4 - BODY_Y
# righe delle liste: il font disegna le lettere ~3 px sotto la y indicata
RIGA_LISTA = 24


# --- file dell'app ----------------------------------------------------------

def leggi_file(nome):
    try:
        with open(nome) as f:
            return f.read()
    except OSError:
        return None


def carica_chiave():
    t = leggi_file("chiave.txt")
    if t is None:
        return None, "Chiave mancante: copia chiave.txt"
    try:
        return P.leggi_chiave(t), None
    except ValueError:
        return None, "chiave.txt non valida"


def carica_comandi():
    # comandi.json e' personale (escluso da git); comandi.example.json e'
    # l'esempio del repo, usato finche' comandi.json non esiste.
    t = leggi_file("comandi.json")
    if t is None:
        t = leggi_file("comandi.example.json")
    if t is None:
        return [], "comandi.json mancante"
    try:
        return C.carica(t)
    except MemoryError:
        return [], "comandi.json troppo grande"


# --- Bluetooth ----------------------------------------------------------

def _adv_payload():
    # flags (LE General Discoverable, BR/EDR non supportato) + UUID 128 bit
    # completo. Il nome va nella scan response: insieme non stanno nei 31 byte.
    payload = bytearray(b"\x02\x01\x06")
    uuid_bytes = bytes(_SVC_UUID)
    payload += bytes((len(uuid_bytes) + 1, 0x07)) + uuid_bytes
    return payload


def _resp_payload():
    name = DEVICE_NAME.encode()
    return bytes((len(name) + 1, 0x09)) + name


class Link:
    def __init__(self, chiave):
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.config(gap_name=DEVICE_NAME)
        try:
            self.ble.config(mtu=247)
        except Exception:  # noqa: BLE001 - optional, not every firmware build supports it
            pass  # resta la MTU minima (20 byte utili per notify)
        self.ble.irq(self._irq)
        ((self.cmd_handle, self.status_handle),) = self.ble.gatts_register_services((
            (_SVC_UUID, (
                (_CMD_UUID, _FLAG_READ | _FLAG_NOTIFY),
                (_STATUS_UUID, _FLAG_WRITE),
            )),
        ))
        self.ble.gatts_set_buffer(self.status_handle, 32)
        self.sessione = P.Sessione(chiave) if chiave else None
        self.conn = None
        self.mtu = 23
        self.usb_ready = False
        self.hello = None          # (versione, impronta) dell'ultimo dongle
        self.esiti = []            # (contatore, esito) ricevuti, letti da update()
        self.coda = []             # pezzi ancora da inviare
        self.need_advertise = True
        self.adv = _adv_payload()
        self.resp = _resp_payload()

    # Chiamata dallo scheduler MicroPython: solo aggiornamento di stato.
    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            if self.conn is None:
                self.conn = conn_handle
                self._azzera()
            else:
                self.ble.gap_disconnect(conn_handle)  # un solo dongle alla volta
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            if conn_handle == self.conn:
                self.conn = None
                self._azzera()
                self.need_advertise = True
        elif event == _IRQ_MTU_EXCHANGED:
            conn_handle, mtu = data
            if conn_handle == self.conn:
                self.mtu = mtu
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, attr_handle = data
            if attr_handle != self.status_handle:
                return
            st = P.leggi_stato(self.ble.gatts_read(self.status_handle))
            if st is None:
                return
            if st[0] == P.ST_USB:
                self.usb_ready = st[1]
            elif st[0] == P.ST_HELLO:
                _, versione, nonce, impronta = st
                self.hello = (versione, impronta)
                if self.sessione and versione == P.VERSIONE and impronta == self.sessione.impronta:
                    self.sessione.avvia(nonce)
            elif st[0] == P.ST_ESITO:
                if len(self.esiti) < 16:
                    self.esiti.append((st[1], st[2]))

    def _azzera(self):
        self.usb_ready = False
        self.hello = None
        self.mtu = 23
        self.coda = []
        self.esiti = []
        if self.sessione:
            self.sessione.nonce = None

    def poll(self):
        if self.need_advertise and self.conn is None:
            try:
                self.ble.gap_advertise(ADV_INTERVAL_US, adv_data=self.adv,
                                       resp_data=self.resp, connectable=True)
                self.need_advertise = False
            except OSError:
                pass  # riprova al prossimo frame
        n = 0
        while self.coda and self.conn is not None and n < PEZZI_PER_FRAME:
            try:
                self.ble.gatts_notify(self.conn, self.cmd_handle, self.coda[0])
            except OSError:
                break  # buffer pieno: stesso pezzo al prossimo frame
            self.coda.pop(0)
            n += 1

    def pronto(self):
        return (self.conn is not None and self.sessione is not None
                and self.sessione.attiva() and self.usb_ready)

    def in_invio(self):
        return bool(self.coda)

    def invia(self, tipo, dati=b""):
        # -> contatore del messaggio, o None se non e' possibile inviare ora
        if not self.pronto() or self.coda:
            return None
        msg = self.sessione.messaggio(tipo, dati)
        self.coda = P.pezzi(msg, min(self.mtu - 3, 244))
        return self.sessione.contatore

    def interrompi_invio(self):
        self.coda = []

    def stato(self):
        # -> (colore, testo, lampeggia)
        if self.sessione is None:
            return ERR_COLOR, errore_chiave, False
        if self.conn is None:
            return WAIT_COLOR, "In attesa del dongle...", True
        if self.hello is None:
            return WAIT_COLOR, "Dongle collegato, avvio sessione...", True
        versione, impronta = self.hello
        if versione != P.VERSIONE:
            return ERR_COLOR, "Versione dongle diversa (v%d)" % versione, False
        if impronta != self.sessione.impronta:
            return ERR_COLOR, "Chiave diversa dal dongle", False
        if not self.usb_ready:
            return WAIT_COLOR, "Dongle OK, USB del PC non pronta", False
        return OK_COLOR, "Dongle pronto", False

    def close(self):
        try:
            self.ble.active(False)
        except Exception:  # noqa: BLE001 - best effort on exit
            pass


chiave, errore_chiave = carica_chiave()
link = Link(chiave)
gruppi, errore_comandi = carica_comandi()

# --- stato dell'interfaccia -----------------------------------------------

MENU, PRES, GRUPPI, VOCI = "menu", "pres", "gruppi", "voci"
schermata = MENU
sel_menu = 0
sel_gruppo = 0
sel_voce = 0

# presentazione (solo lato badge, indicativa)
slide = 1
show_running = False
show_start_ms = 0
black = False

toast_text = ""
toast_color = TEXT_COLOR
toast_until = 0

# comando in corso: {"contatore", "nome", "fase": "invio"|"attesa"|"esecuzione", "t"}
attivo = None
etichette = {}  # contatore -> nome, per gli errori dei comandi brevi

hold_start = {}
long_fired = {}
repeat_at = {}


def toast(text, col):
    global toast_text, toast_color, toast_until
    toast_text = text
    toast_color = col
    toast_until = badge.ticks + TOAST_MS


def vai(nuova):
    global schermata, slide, show_running, black
    schermata = nuova
    hold_start.clear()
    long_fired.clear()
    if nuova == PRES:
        slide = 1
        show_running = False
        black = False


# --- invio comandi ---------------------------------------------------------

def motivo_non_pronto():
    colore, testo, _ = link.stato()
    return testo if colore != OK_COLOR else "Dongle occupato"


def invia_presentazione(nome, etichetta):
    if attivo is not None:
        toast("Attendi la fine del comando", WAIT_COLOR)
        return False
    contatore = link.invia(P.TIPO_MACRO, C.PRESENTAZIONE[nome])
    if contatore is None:
        toast(motivo_non_pronto(), ERR_COLOR)
        return False
    etichette[contatore] = etichetta
    if len(etichette) > 20:
        etichette.pop(min(etichette))
    toast(etichetta, ACCENT_COLOR)
    return True


def invia_voce(voce):
    global attivo
    if voce["errore"]:
        toast("Voce non valida, vedi comandi.json", ERR_COLOR)
        return
    if attivo is not None:
        return
    contatore = link.invia(P.TIPO_MACRO, voce["dati"])
    if contatore is None:
        toast(motivo_non_pronto(), ERR_COLOR)
        return
    attivo = {"contatore": contatore, "nome": voce["nome"], "fase": "invio", "t": badge.ticks}


def annulla_voce():
    global attivo
    if attivo is None:
        return
    if attivo["fase"] == "invio":
        # il dongle scarta il messaggio incompleto al prossimo inizio
        link.interrompi_invio()
        attivo = None
        toast("Annullato", WAIT_COLOR)
        return
    link.invia(P.TIPO_ANNULLA)
    attivo["fase"] = "annullo"


def gestisci_esiti():
    global attivo
    if attivo is not None:
        if link.conn is None:
            attivo = None
            toast("Dongle scollegato", ERR_COLOR)
        elif attivo["fase"] == "invio" and not link.in_invio():
            attivo["fase"] = "attesa"
            attivo["t"] = badge.ticks
        elif attivo["fase"] == "attesa" and badge.ticks - attivo["t"] > TIMEOUT_RISPOSTA_MS:
            attivo = None
            toast("Nessuna risposta dal dongle", ERR_COLOR)
    while link.esiti:
        contatore, esito = link.esiti.pop(0)
        testo = P.ESITO_TESTO.get(esito, "Errore 0x%02x" % esito)
        if attivo is not None and contatore == attivo["contatore"]:
            if esito == P.ESITO_IN_CORSO:
                attivo["fase"] = "esecuzione"
                continue
            attivo = None
            toast(testo, OK_COLOR if esito == P.ESITO_FATTO else
                  WAIT_COLOR if esito == P.ESITO_ANNULLATO else ERR_COLOR)
        elif esito not in (P.ESITO_FATTO, P.ESITO_IN_CORSO):
            # errore su un comando della presentazione (o su un messaggio rotto)
            nome = etichette.get(contatore)
            toast((nome + ": " if nome else "") + testo, ERR_COLOR)


# --- pulsanti ---------------------------------------------------------------

def pressione(button):
    # -> None, "breve" (al rilascio) o "lunga" (dopo LONG_PRESS_MS)
    now = badge.ticks
    if badge.pressed(button):
        hold_start[button] = now
        long_fired[button] = False
    start = hold_start.get(button)
    if start is None:
        return None
    if badge.held(button) and not long_fired[button] and now - start >= LONG_PRESS_MS:
        long_fired[button] = True
        return "lunga"
    if badge.released(button):
        hold_start[button] = None
        if not long_fired[button]:
            return "breve"
    return None


def scorri(button):
    # True al primo tocco e poi ripetuto se il tasto resta premuto
    now = badge.ticks
    if badge.pressed(button):
        repeat_at[button] = now + REPEAT_DELAY_MS
        return True
    if badge.held(button) and now >= repeat_at.get(button, now + 1):
        repeat_at[button] = now + REPEAT_MS
        return True
    return False


def muovi(sel, n):
    if n == 0:
        return 0
    if scorri(BUTTON_UP):
        sel = (sel - 1) % n
    if scorri(BUTTON_DOWN):
        sel = (sel + 1) % n
    return sel


def tasti_menu():
    global sel_menu, gruppi, errore_comandi
    sel_menu = muovi(sel_menu, 2)
    if badge.pressed(BUTTON_B) or badge.pressed(BUTTON_C):
        if sel_menu == 0:
            vai(PRES)
        else:
            vai(GRUPPI)


def tasti_pres():
    global slide, show_running, show_start_ms, black
    azioni = []
    if badge.pressed(BUTTON_C):
        azioni.append("avanti")
    p = pressione(BUTTON_A)
    if p == "breve":
        azioni.append("indietro")
    elif p == "lunga":
        vai(MENU)
        return
    p = pressione(BUTTON_UP)
    if p:
        azioni.append("indietro" if p == "breve" else "avvio")
    p = pressione(BUTTON_DOWN)
    if p:
        azioni.append("avanti" if p == "breve" else "fine")
    p = pressione(BUTTON_B)
    if p:
        azioni.append("nero" if p == "breve" else "avvio_qui")

    etichette_pres = {"avanti": "Avanti", "indietro": "Indietro", "avvio": "Avvio (F5)",
                      "avvio_qui": "Avvio da qui", "fine": "Fine (Esc)", "nero": "Schermo nero"}
    for a in azioni:
        if not invia_presentazione(a, etichette_pres[a]):
            continue
        if a == "avanti":
            slide += 1
            black = False
        elif a == "indietro":
            slide = max(1, slide - 1)
            black = False
        elif a == "avvio":
            slide = 1
            show_running = True
            show_start_ms = badge.ticks
            black = False
        elif a == "avvio_qui":
            show_running = True
            show_start_ms = badge.ticks
            black = False
        elif a == "fine":
            show_running = False
            black = False
        elif a == "nero":
            black = not black


def tasti_gruppi():
    global sel_gruppo, sel_voce, gruppi, errore_comandi
    if badge.pressed(BUTTON_A):
        vai(MENU)
        return
    if errore_comandi:
        if badge.pressed(BUTTON_B):
            gruppi, errore_comandi = carica_comandi()
            sel_gruppo = 0
            toast("File ricaricato" if not errore_comandi else "Ancora errori", WAIT_COLOR)
        return
    sel_gruppo = muovi(sel_gruppo, len(gruppi))
    if badge.pressed(BUTTON_B):
        sel_voce = 0
        vai(VOCI)


def tasti_voci():
    global sel_voce
    voci = gruppi[sel_gruppo]["comandi"]
    if attivo is not None:
        if badge.pressed(BUTTON_A):
            annulla_voce()
        return
    if badge.pressed(BUTTON_A):
        vai(GRUPPI)
        return
    sel_voce = muovi(sel_voce, len(voci))
    if badge.pressed(BUTTON_B) and voci:
        invia_voce(voci[sel_voce])


# --- disegno ------------------------------------------------------------

def testo(msg, x, y, f=None, size=1):
    screen.font = f or FONT_TESTO
    screen.text(msg, x, y, size)


def larghezza(msg, f=None, size=1):
    screen.font = f or FONT_TESTO
    return screen.measure_text(msg, size)[0]


def testo_destra(msg, x_right, y, f=None, size=1):
    testo(msg, x_right - larghezza(msg, f, size), y, f, size)


def testo_centro(msg, y, f=None, size=1):
    testo(msg, (W - larghezza(msg, f, size)) // 2, y, f, size)


def taglia(msg, max_w, f=None):
    if larghezza(msg, f) <= max_w:
        return msg
    while msg and larghezza(msg + "...", f) > max_w:
        msg = msg[:-1]
    return msg + "..."


def pannello(x, y, w, h, r, col):
    screen.pen = col
    screen.shape(shape.rounded_rectangle(x, y, w, h, r))


def disegna_batteria(x_right, y):
    level = badge.battery_level()
    usb = badge.usb_connected()
    if usb:
        label = "USB" if not badge.is_charging() else "carica"
        col = OK_COLOR
    else:
        label = "%d%%" % level
        col = ERR_COLOR if level < 15 else WAIT_COLOR if level < 35 else OK_COLOR
    # icona: corpo 22x11 + polo, abbassata per allinearla alla scritta
    bx = x_right - 26
    y += 3
    screen.pen = DIM_TEXT_COLOR
    screen.shape(shape.rounded_rectangle(bx, y, 22, 11, 2))
    screen.shape(shape.rectangle(bx + 22, y + 3, 3, 5))
    screen.pen = PANEL_COLOR
    screen.shape(shape.rectangle(bx + 1, y + 1, 20, 9))
    screen.pen = col
    fill = 100 if usb else max(5, min(100, level))
    screen.shape(shape.rectangle(bx + 2, y + 2, max(1, 18 * fill // 100), 7))
    screen.pen = TEXT_COLOR
    testo_destra(label, bx - 6, y - 2, FONT_TITOLO)


TITOLI = {MENU: "PRESENTATOR", PRES: "PRESENTAZIONE", GRUPPI: "INVIA COMANDI"}


def disegna_testata():
    pannello(8, HEADER_Y, W - 16, HEADER_H, 10, PANEL_COLOR)
    titolo = TITOLI.get(schermata)
    if schermata == VOCI:
        titolo = taglia("COMANDI > " + C.per_schermo(gruppi[sel_gruppo]["nome"]), 190, FONT_TITOLO)
    screen.pen = TEXT_COLOR
    testo(titolo, 18, HEADER_Y + 7, FONT_TITOLO)
    disegna_batteria(W - 18, HEADER_Y + 7)
    # riga di stato del dongle
    col, msg, lampeggia = link.stato()
    on = not lampeggia or (badge.ticks // 500) % 2 == 0
    screen.pen = col if on else PANEL_COLOR
    screen.shape(shape.circle(24, HEADER_Y + 31, 4))
    screen.pen = col
    testo(taglia(msg, W - 60, FONT_PICCOLO), 34, HEADER_Y + 31 - FH_PICCOLO // 2, FONT_PICCOLO)


def chip(label, x, y):
    w = larghezza(label, FONT_PICCOLO) + 8
    pannello(x, y, w, CHIP_H, 3, CHIP_COLOR)
    screen.pen = CHIP_TEXT
    testo(label, x + 4, y + 2, FONT_PICCOLO)
    return w


def righe_legenda(voci):
    # -> lista di (voci della riga, altezza riga)
    out = []
    for r in range(0, min(len(voci), 6), 3):
        riga = voci[r:r + 3]
        out.append((riga, RIGA_LEGENDA if any(v[2] for v in riga) else RIGA_LEGENDA_CORTA))
    return out


def altezza_legenda(voci):
    return 6 + sum(h for _, h in righe_legenda(voci))


def legenda():
    # tasti della schermata corrente: (tasto, azione, azione_tenuto o None)
    if schermata == MENU:
        return [("SU/GIU", "Scegli", None), ("B", "Apri", None), ("HOME", "Esci app", None)]
    if schermata == PRES:
        return [("A", "Indietro", "Menu"), ("B", "Nero", "Da qui"), ("C", "Avanti", None),
                ("SU", "Indietro", "Avvia"), ("GIU", "Avanti", "Fine")]
    if schermata == GRUPPI:
        if errore_comandi:
            return [("A", "Menu", None), ("B", "Ricarica", None)]
        return [("SU/GIU", "Scorri", None), ("B", "Apri gruppo", None), ("A", "Menu", None)]
    if attivo is not None:
        return [("A", "Annulla", None)]
    return [("SU/GIU", "Scorri", None), ("B", "Invia al PC", None), ("A", "Gruppi", None)]


def disegna_legenda(voci):
    pannello(8, LEGEND_Y, W - 16, H - LEGEND_Y - 4, 10, PANEL_COLOR)
    col_w = (W - 24) // 3
    y = LEGEND_Y + 5
    for riga, alt in righe_legenda(voci):
        for c, (tasto, azione, tenuto) in enumerate(riga):
            disegna_voce_legenda(14 + c * col_w, y, col_w, tasto, azione, tenuto)
        y += alt


def disegna_voce_legenda(x, y, col_w, tasto, azione, tenuto):
    w = chip(tasto, x, y)
    screen.pen = TEXT_COLOR
    testo(taglia(azione, col_w - w - 8, FONT_PICCOLO), x + w + 4, y + 2, FONT_PICCOLO)
    if tenuto:
        screen.pen = DIM_TEXT_COLOR
        testo(taglia("tieni: " + tenuto, col_w - 4, FONT_PICCOLO), x + 2, y + CHIP_H + 2, FONT_PICCOLO)


def disegna_toast():
    if badge.ticks >= toast_until or not toast_text:
        return
    if schermata == PRES:
        # in alto al centro, tra le scritte SLIDE e TEMPO
        msg = taglia(C.per_schermo(toast_text), W - 150, FONT_TITOLO)
        w = larghezza(msg, FONT_TITOLO) + 24
        pannello((W - w) // 2, BODY_Y + 4, w, 26, 8, BG_COLOR)
        screen.pen = toast_color
        testo_centro(msg, BODY_Y + 12, FONT_TITOLO)
        return
    # altrove: sostituisce l'ultima riga del corpo (la descrizione della voce)
    y = BODY_Y + BODY_H - 18
    screen.pen = BG_COLOR
    screen.shape(shape.rectangle(8, y, W - 16, 22))  # fino alla legenda
    screen.pen = toast_color
    testo_centro(taglia(C.per_schermo(toast_text), W - 40, FONT_TITOLO), y + 1, FONT_TITOLO)


def disegna_lista(righe, sel, y0, n_visibili, alt=20):
    # righe: lista di (testo, colore). Scorre per tenere visibile la selezione.
    if not righe:
        return
    primo = min(max(0, sel - n_visibili // 2), max(0, len(righe) - n_visibili))
    for k in range(n_visibili):
        i = primo + k
        if i >= len(righe):
            break
        y = y0 + k * alt
        msg, col = righe[i]
        if i == sel:
            pannello(12, y, W - 24, alt - 2, 6, SEL_COLOR)
        screen.pen = col
        testo(taglia(C.per_schermo(msg), W - 60, FONT_TITOLO), 22, y + 1, FONT_TITOLO)
    screen.pen = DIM_TEXT_COLOR
    if primo > 0:
        testo("^", W - 26, y0 + 1, FONT_TITOLO)
    if primo + n_visibili < len(righe):
        testo("v", W - 26, y0 + (n_visibili - 1) * alt + 1, FONT_TITOLO)


def disegna_menu():
    voci = ("Gestisci presentazione", "Invia comandi")
    for i, v in enumerate(voci):
        y = BODY_Y + 8 + i * 40
        pannello(12, y, W - 24, 34, 8, SEL_COLOR if i == sel_menu else PANEL_COLOR)
        screen.pen = TEXT_COLOR if i == sel_menu else DIM_TEXT_COLOR
        testo("%d) %s" % (i + 1, v), 26, y + 9, FONT_TITOLO, 1)


def fmt_elapsed(ms):
    s = ms // 1000
    if s >= 3600:
        return "{}:{:02d}:{:02d}".format(s // 3600, (s // 60) % 60, s % 60)
    return "{:02d}:{:02d}".format(s // 60, s % 60)


def disegna_pres():
    # pannello fino alla legenda; i messaggi compaiono in alto tra SLIDE e TEMPO.
    # font.height e' piu' alto del glyph disegnato: posizioni verificate sul badge
    alt = BODY_H - 4
    pannello(8, BODY_Y, W - 16, alt, 12, PANEL_COLOR)
    fondo = BODY_Y + alt - 6  # i numeri grandi poggiano qui, dentro il pannello
    if black:
        screen.pen = TEXT_COLOR
        testo_centro("SCHERMO NERO", BODY_Y + 30, FONT_TITOLO, 3)  # sotto i messaggi
        screen.pen = DIM_TEXT_COLOR
        testo_centro("premi B per ripristinare", fondo - 10)
    else:
        screen.pen = DIM_TEXT_COLOR
        testo("SLIDE", 24, BODY_Y + 8)
        testo_destra("TEMPO", W - 24, BODY_Y + 8)
        screen.pen = TEXT_COLOR
        testo(str(slide), 24, fondo - FONT_TITOLO.height * 5, FONT_TITOLO, 5)
        if show_running:
            elapsed = fmt_elapsed(badge.ticks - show_start_ms)
            screen.pen = TEXT_COLOR
        else:
            elapsed = "--:--"
            screen.pen = DIM_TEXT_COLOR
        testo_destra(elapsed, W - 24, fondo - FONT_TITOLO.height * 3, FONT_TITOLO, 3)


def disegna_errore_comandi():
    screen.pen = ERR_COLOR
    testo("Errore in comandi.json", 20, BODY_Y + 8, FONT_TITOLO)
    screen.pen = TEXT_COLOR
    screen.font = FONT_TESTO
    screen.text(C.per_schermo(errore_comandi), rect(20, BODY_Y + 30, W - 40, 60), 1)
    screen.pen = DIM_TEXT_COLOR
    testo("Correggi il file in Disk Mode", 20, BODY_Y + 96)


def disegna_gruppi():
    if errore_comandi:
        disegna_errore_comandi()
        return
    righe = [("%s  (%d)" % (g["nome"], len(g["comandi"])), TEXT_COLOR) for g in gruppi]
    disegna_lista(righe, sel_gruppo, BODY_Y + 2, (BODY_H - 4) // RIGA_LISTA, RIGA_LISTA)


def disegna_voci():
    voci = gruppi[sel_gruppo]["comandi"]
    if attivo is not None:
        # comando in corso: al posto della lista, un riquadro con fase e nome
        fase = {"invio": "Invio al dongle...", "attesa": "Invio al dongle...",
                "esecuzione": "Scrittura sul PC...", "annullo": "Annullamento..."}[attivo["fase"]]
        pannello(8, BODY_Y, W - 16, BODY_H - 4, 12, PANEL_COLOR)
        screen.pen = WAIT_COLOR
        testo_centro(fase, BODY_Y + BODY_H // 2 - 26, FONT_TITOLO, 2)
        screen.pen = TEXT_COLOR
        testo_centro(taglia(C.per_schermo(attivo["nome"]), W - 60, FONT_TITOLO),
                     BODY_Y + BODY_H // 2 + 8, FONT_TITOLO)
        return
    righe = [(v["nome"], ERR_COLOR if v["errore"] else TEXT_COLOR) for v in voci]
    # l'ultima riga del corpo e' per la descrizione della voce selezionata
    disegna_lista(righe, sel_voce, BODY_Y + 2, (BODY_H - 18) // RIGA_LISTA, RIGA_LISTA)
    if voci:
        v = voci[sel_voce]
        if v["errore"]:
            screen.pen = ERR_COLOR
            info = "Errore: " + v["errore"]
        else:
            screen.pen = DIM_TEXT_COLOR
            info = v["info"]
        testo(taglia(C.per_schermo(info), W - 40), 20, BODY_Y + BODY_H - 12)


def update():
    global LEGEND_Y, BODY_H
    link.poll()
    gestisci_esiti()
    if schermata == MENU:
        tasti_menu()
    elif schermata == PRES:
        tasti_pres()
    elif schermata == GRUPPI:
        tasti_gruppi()
    else:
        tasti_voci()

    voci_legenda = legenda()
    LEGEND_Y = H - 4 - altezza_legenda(voci_legenda)
    BODY_H = LEGEND_Y - 4 - BODY_Y

    screen.pen = BG_COLOR
    screen.clear()
    disegna_testata()
    if schermata == MENU:
        disegna_menu()
    elif schermata == PRES:
        disegna_pres()
    elif schermata == GRUPPI:
        disegna_gruppi()
    else:
        disegna_voci()
    disegna_legenda(voci_legenda)
    disegna_toast()


def on_exit():
    link.close()


run(update)
