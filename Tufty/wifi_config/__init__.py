# wifi_config - l'unico gestore delle reti WiFi del badge.
#
# Prova le reti note (/multi_secrets.py), poi permette di cambiare rete,
# aggiungerne una (scansione + tastiera virtuale), eliminarla o reimportare
# l'elenco da /system/multi_secrets.py. Tiene /secrets.py allineato alla rete in
# uso: le altre app si collegano solo con quello (wifi.connect() senza argomenti).
# Design: docs/superpowers/specs/2026-10-31-wifi-config-gestione-reti-design.md
# Uso e file: docs/wifi-config.md
import os
import sys

sys.path.insert(0, "/system/apps/wifi_config")
try:
    os.chdir("/system/apps/wifi_config")
except OSError:
    pass

import network

import rete
import reti
import ui
from tastiera import Ripetitore, Tastiera

badge.mode(HIRES | VSYNC)
screen.antialias = image.X2
screen.font = font.sins

TIMEOUT_NOTA = 8000
TIMEOUT_NUOVA = 15000

MOTIVI = {
    "password": "Password errata: correggi e riprova",
    "non_trovata": "Rete non trovata: riprova",
    "fallita": "Connessione non riuscita: controlla la password",
}

coll = rete.Collegamento(network)
rip = Ripetitore((BUTTON_A, BUTTON_C, BUTTON_UP, BUTTON_DOWN))
note, stato_file, n_importate = reti.carica()

# stato della macchina a schermate
S = {
    "schermata": None,
    "sel": 0,
    "connessa": None,       # (ssid, password) della rete in uso, o None
    "coda": [],             # reti note ancora da provare
    "tentativo": None,      # (ssid, password) in prova
    "avviato": False,
    "dopo_fallimento": None,
    "elenco": [],           # risultato della scansione
    "origine": "nessuna",   # da dove si e' entrati in "Aggiungi rete"
    "precedente": None,     # rete a cui tornare se l'aggiunta/cambio non riesce
    "tastiera": None,
    "msg": None,
    "msg_col": None,
    "modo_note": "cambia",  # SCEGLI_NOTA: "cambia" o "elimina"
    "visibili": {},         # ssid -> livello, per la lista delle reti note
    "da_eliminare": None,
    "da_svuotare": None,    # ssid che /secrets.py contiene ma che e' stato eliminato
    "messaggio": None,      # (righe, colore, schermata successiva)
    "scansione_fatta": False,
}


def vai(schermata, sel=0):
    S["schermata"] = schermata
    S["sel"] = sel
    S["avviato"] = False
    S["scansione_fatta"] = False


def mostra(righe, colore, poi):
    S["messaggio"] = (righe, colore, poi)
    vai("MESSAGGIO")


def ssid_note():
    return {n["ssid"] for n in note}


def password_nota(ssid):
    for n in note:
        if n["ssid"] == ssid:
            return n["password"]
    return ""


# --------------------------------------------------------------- avvio
def inizia():
    if stato_file == "danneggiato":
        vai("DANNEGGIATO")
    elif not note:
        vai("NESSUNA")
    else:
        prova_note()


def prova_note():
    S["coda"] = [(n["ssid"], n["password"]) for n in note]
    S["tentativo"] = None
    vai("PROVA_NOTE")


def riuscita(ssid, password):
    global note
    note = reti.in_cima(note, ssid, password)
    reti.salva(note)
    reti.allinea_secrets(ssid, password)
    S["connessa"] = (ssid, password)
    S["da_svuotare"] = None
    S["precedente"] = None
    vai("MENU")


def nessuna_riuscita():
    S["connessa"] = None
    if S["da_svuotare"] and reti.ssid_secrets() == S["da_svuotare"]:
        reti.svuota_secrets()
    S["da_svuotare"] = None
    vai("NESSUNA")


# --------------------------------------------------------------- schermate
def schermata_avviso(ev):
    ui.titolo("WiFi Config")
    ui.pannello(16, 46, ui.W - 32, 128)
    if stato_file == "importato":
        ui.centrato("Reti importate: {}".format(n_importate), 60, ui.OK)
    ui.centrato("Il file multi_secrets.py sul badge", 88)
    ui.centrato("non viene piu' usato:", 106)
    ui.centrato("puoi eliminarlo (Disk Mode).", 124)
    ui.centrato("Le reti si gestiscono da qui.", 150, ui.DIM)
    ui.piede("B: continua")
    if BUTTON_B in ev:
        inizia()


def schermata_danneggiato(ev):
    ui.titolo("WiFi Config")
    ui.pannello(16, 56, ui.W - 32, 100)
    ui.centrato("Elenco reti danneggiato", 74, ui.ERR)
    ui.centrato("Usa Reimporta da multi_secrets", 100)
    ui.centrato("o aggiungi una rete", 118)
    ui.piede("B: continua")
    if BUTTON_B in ev:
        vai("MENU")


def schermata_prova_note(_ev):
    ora = badge.ticks
    if S["tentativo"] is None:
        if not S["coda"]:
            nessuna_riuscita()
            return
        S["tentativo"] = S["coda"].pop(0)
        coll.avvia(S["tentativo"][0], S["tentativo"][1], TIMEOUT_NOTA, ora)
    tot = len(note)
    pos = tot - len(S["coda"])
    ui.titolo("WiFi Config")
    ui.centrato("Connessione alle reti note...", 70)
    ui.centrato("Rete {}/{}: {}".format(pos, tot, S["tentativo"][0]), 92, ui.DIM)
    ui.spinner(ui.W // 2, 150, ora)
    ui.piede("HOME: torna al menu")
    esito = coll.esito(ora)
    if esito == "ok":
        riuscita(*S["tentativo"])
    elif esito is not None:
        S["tentativo"] = None


def schermata_nessuna(ev):
    voci = ["Si, cerca le reti", "Gestisci reti note", "No"]
    ui.titolo("WiFi Config")
    if note:
        ui.centrato("Nessuna rete nota ha risposto", 58, ui.ERR)
    else:
        ui.centrato("Nessuna rete salvata", 58, ui.ERR)
    ui.centrato("Vuoi aggiungere una nuova rete?", 84)
    ui.menu(110, voci, S["sel"])
    ui.piede("SU/GIU scegli   B conferma")
    S["sel"] = scorri(ev, S["sel"], len(voci))
    if BUTTON_B in ev:
        if S["sel"] == 0:
            entra_aggiunta("nessuna")
        elif S["sel"] == 1:
            vai("MENU")
        else:
            vai("NON_CONNESSO")


def scorri(ev, sel, n):
    if n == 0:
        return 0
    if BUTTON_UP in ev:
        sel = (sel - 1) % n
    if BUTTON_DOWN in ev:
        sel = (sel + 1) % n
    return sel


# ---- aggiunta di una rete
def entra_aggiunta(origine):
    S["origine"] = origine
    S["precedente"] = S["connessa"] if coll.connesso() else None
    S["msg"] = None
    vai("SCANSIONE")


def esci_aggiunta():
    if coll.connesso() and S["connessa"]:
        vai("MENU")
    elif S["precedente"]:
        S["tentativo"] = S["precedente"]
        vai("RITORNO")
    elif S["origine"] == "menu":
        vai("MENU")
    else:
        vai("NESSUNA")


def schermata_scansione(_ev):
    ui.titolo("Aggiungi rete")
    ui.centrato("Ricerca reti WiFi...", 80)
    ui.spinner(ui.W // 2, 135, badge.ticks)
    if not S["avviato"]:
        S["avviato"] = True  # prima si disegna lo spinner, la scansione blocca
        return
    if not (S["connessa"] and coll.connesso()):
        coll.scollega()  # nessun tentativo rimasto attivo nel chip durante la scansione
    try:
        grezza = coll.scansiona()
    except Exception:  # noqa: BLE001 - a failed scan shows an empty list
        grezza = []
    S["elenco"] = rete.elabora_scansione(grezza, ssid_note())
    vai("ELENCO")


def schermata_elenco(ev):
    elenco = S["elenco"]
    n = len(elenco)
    ui.titolo("Aggiungi rete", "{} reti".format(n))
    if not n:
        ui.centrato("Nessuna rete trovata", 90, ui.DIM)
    top = ui.finestra(S["sel"], n)
    y = 36
    for i in range(top, min(n, top + ui.RIGHE_LISTA)):
        r = elenco[i]
        on = i == S["sel"]
        fg = ui.riga_lista(y, on)
        ui.segnale(14, y + 4, r["livello"])
        screen.pen = fg
        screen.text(ui.tronca(r["ssid"], 196), 36, y + 6)
        if r["nota"]:
            ui.stella(ui.W - 46, y + 4, ui.SEL_TXT if on else ui.SEL)
        if r["aperta"]:
            ui.scritta_destra("aperta", y + 6, ui.SEL_TXT if on else ui.OK, 62)
        else:
            ui.lucchetto(ui.W - 28, y + 4, fg)
        y += 25
    if S["msg"]:
        ui.centrato(S["msg"], ui.H - 32, ui.ERR)
    ui.piede("B scegli   A indietro   C ripeti ricerca")
    S["sel"] = scorri(ev, S["sel"], n)
    if BUTTON_A in ev:
        esci_aggiunta()
    elif BUTTON_C in ev:
        S["msg"] = None
        vai("SCANSIONE")
    elif BUTTON_B in ev and n:
        r = elenco[S["sel"]]
        S["msg"] = None
        S["sel_elenco"] = S["sel"]
        if r["aperta"]:
            prova_nuova(r["ssid"], "")
        else:
            S["tastiera"] = Tastiera(password_nota(r["ssid"]) if r["nota"] else "")
            S["tastiera"].ssid = r["ssid"]
            if r["nota"]:
                S["msg"], S["msg_col"] = "Password salvata: OK per provarla", ui.ACC
            vai("TASTIERA")


def schermata_tastiera(ev):
    t = S["tastiera"]
    for k in ev:
        if k == BUTTON_A:
            t.muovi(0, -1)
        elif k == BUTTON_C:
            t.muovi(0, 1)
        elif k == BUTTON_UP:
            t.muovi(-1, 0)
        elif k == BUTTON_DOWN:
            t.muovi(1, 0)
        elif k == BUTTON_B:
            esito = t.premi()
            S["msg"] = None
            if esito == "corta":
                S["msg"], S["msg_col"] = "Servono almeno 8 caratteri", ui.SEL
            elif esito == "ok":
                prova_nuova(t.ssid, t.testo)
                return
            elif esito == "annulla":
                vai("ELENCO", S["sel_elenco"])
                return
    t.disegna(t.ssid, S["msg"], S["msg_col"])


def prova_nuova(ssid, password):
    S["tentativo"] = (ssid, password)
    S["sel_elenco"] = S["sel"] if S["schermata"] == "ELENCO" else S.get("sel_elenco", 0)
    vai("PROVA_NUOVA")


def schermata_prova_nuova(_ev):
    ora = badge.ticks
    ssid, password = S["tentativo"]
    if not S["avviato"]:
        S["avviato"] = True
        S["connessa"] = None
        coll.avvia(ssid, password, TIMEOUT_NUOVA, ora)
    ui.titolo("Connessione", ui.tronca(ssid, 190))
    ui.centrato("Prova della password..." if password else "Collegamento alla rete aperta...", 80)
    ui.spinner(ui.W // 2, 135, ora)
    ui.piede("attendere fino a 15 s")
    esito = coll.esito(ora)
    if esito == "ok":
        riuscita(ssid, password)
    elif esito is not None:
        if not password:
            S["msg"] = "Connessione non riuscita"
            vai("ELENCO", S["sel_elenco"])
        else:
            S["msg"], S["msg_col"] = MOTIVI[esito], ui.ERR
            vai("TASTIERA")


# ---- menu e reti note
def schermata_menu(ev):
    connesso = coll.connesso() and S["connessa"] is not None
    ui.titolo("WiFi Config")
    ui.pannello(10, 38, ui.W - 20, 50, 8)
    if connesso:
        ui.pallino(30, 63, ui.OK)
        screen.pen = ui.TXT
        screen.text(ui.tronca("Connesso a {}".format(S["connessa"][0]), 214), 46, 48)
        screen.pen = ui.DIM
        screen.text("IP {}".format(coll.ip() or "?"), 46, 66)
        try:
            ui.segnale(ui.W - 40, 56, rete.livello(coll.wlan.status("rssi")))
        except Exception:  # noqa: BLE001 - the signal icon is optional
            pass
        voci = ["Cambia rete"]
    else:
        ui.pallino(30, 63, ui.ERR)
        screen.pen = ui.TXT
        screen.text("Non connesso", 46, 48)
        screen.pen = ui.DIM
        screen.text("Nessuna rete nota ha risposto" if note else "Nessuna rete salvata", 46, 66)
        voci = ["Collega a una rete nota"]
    voci += ["Aggiungi rete", "Elimina rete", "Reimporta da multi_secrets"]
    ui.menu(98, voci, S["sel"])
    ui.piede("HOME: torna al menu")
    S["sel"] = scorri(ev, S["sel"], len(voci))
    if BUTTON_B in ev:
        if S["sel"] in (0, 2) and not note:
            mostra(["Nessuna rete salvata"], ui.DIM, "MENU")
        elif S["sel"] == 0:
            S["modo_note"] = "cambia"
            vai("SCEGLI_NOTA")
        elif S["sel"] == 1:
            entra_aggiunta("menu")
        elif S["sel"] == 2:
            S["modo_note"] = "elimina"
            vai("SCEGLI_NOTA")
        else:
            vai("CONFERMA_REIMPORTA", 0)


def schermata_scegli_nota(ev):
    if not S["scansione_fatta"]:
        # primo frame: messaggio, poi scansione (blocca) per le barre del segnale
        ui.titolo("Reti note")
        ui.centrato("Ricerca reti WiFi...", 80)
        ui.spinner(ui.W // 2, 135, badge.ticks)
        if S["avviato"]:
            if not (S["connessa"] and coll.connesso()):
                coll.scollega()
            try:
                S["visibili"] = {r["ssid"]: r["livello"] for r in
                                     rete.elabora_scansione(coll.scansiona(), ssid_note())}
            except Exception:  # noqa: BLE001 - a failed scan shows no signal levels
                S["visibili"] = {}
            S["scansione_fatta"] = True
        S["avviato"] = True
        return

    cambia = S["modo_note"] == "cambia"
    connesso = coll.connesso() and S["connessa"] is not None
    in_uso = S["connessa"][0] if connesso else None
    titolo = ("Cambia rete" if connesso else "Collega a una rete") if cambia else "Elimina rete"
    n = len(note)
    ui.titolo(titolo, "{} note".format(n))
    top = ui.finestra(S["sel"], n)
    y = 38
    for i in range(top, min(n, top + ui.RIGHE_LISTA)):
        ssid = note[i]["ssid"]
        on = i == S["sel"]
        fg = ui.riga_lista(y, on)
        ui.segnale(14, y + 4, S["visibili"].get(ssid, 0))
        screen.pen = fg
        screen.text(ui.tronca(ssid, 170), 36, y + 6)
        if ssid == in_uso:
            ui.scritta_destra("in uso", y + 6, ui.SEL_TXT if on else ui.OK)
        elif ssid not in S["visibili"]:
            ui.scritta_destra("non visibile", y + 6, ui.SEL_TXT if on else ui.DIM)
        y += 26
    ui.piede(("B collega" if cambia else "B elimina") + "   A indietro")
    S["sel"] = scorri(ev, S["sel"], n)
    if BUTTON_A in ev:
        vai("MENU")
    elif BUTTON_B in ev and n:
        scelta = note[S["sel"]]
        if not cambia:
            S["da_eliminare"] = scelta["ssid"]
            vai("CONFERMA_ELIMINA", 0)
        elif scelta["ssid"] != in_uso:
            S["precedente"] = S["connessa"] if connesso else None
            S["tentativo"] = (scelta["ssid"], scelta["password"])
            vai("PROVA_CAMBIO")


def schermata_prova_cambio(_ev):
    ora = badge.ticks
    ssid, password = S["tentativo"]
    if not S["avviato"]:
        S["avviato"] = True
        S["connessa"] = None
        coll.avvia(ssid, password, TIMEOUT_NOTA, ora)
    ui.titolo("Connessione", ui.tronca(ssid, 190))
    ui.centrato(ui.tronca("Collegamento a {}...".format(ssid), 300), 80)
    ui.spinner(ui.W // 2, 135, ora)
    esito = coll.esito(ora)
    if esito == "ok":
        riuscita(ssid, password)
    elif esito is not None:
        poi = "RITORNO" if S["precedente"] else "MENU"
        if S["precedente"]:
            S["tentativo"] = S["precedente"]
        mostra([ui.tronca("Connessione a {}".format(ssid), 270), "non riuscita"], ui.ERR, poi)


def schermata_ritorno(_ev):
    ora = badge.ticks
    ssid, password = S["tentativo"]
    if not S["avviato"]:
        S["avviato"] = True
        coll.avvia(ssid, password, TIMEOUT_NOTA, ora)
    ui.titolo("WiFi Config")
    ui.centrato(ui.tronca("Ritorno a {}...".format(ssid), 300), 80)
    ui.spinner(ui.W // 2, 135, ora)
    esito = coll.esito(ora)
    if esito == "ok":
        riuscita(ssid, password)
    elif esito is not None:
        S["precedente"] = None
        prova_note()


def schermata_conferma_elimina(ev):
    ssid = S["da_eliminare"]
    ui.titolo("Elimina rete")
    ui.pannello(30, 60, ui.W - 60, 110)
    ui.centrato("Eliminare la rete", 74)
    ui.centrato(ui.tronca('"{}"?'.format(ssid), 240), 94, ui.SEL)
    ui.centrato("La password salvata verra' persa", 116, ui.DIM)
    ui.pulsanti(140, ["No", "Si, elimina"], S["sel"])
    ui.piede("A/C scegli   B conferma")
    if BUTTON_A in ev or BUTTON_C in ev:
        S["sel"] = 1 - S["sel"]
    if BUTTON_B in ev:
        if S["sel"] == 0:
            vai("SCEGLI_NOTA")
            S["scansione_fatta"] = True
        else:
            elimina(ssid)


def elimina(ssid):
    global note
    note = reti.togli(note, ssid)
    reti.salva(note)
    in_uso = S["connessa"] is not None and S["connessa"][0] == ssid and coll.connesso()
    if in_uso:
        coll.scollega()
        S["connessa"] = None
        S["da_svuotare"] = ssid
        if note:
            prova_note()
        else:
            nessuna_riuscita()
        return
    if reti.ssid_secrets() == ssid:
        if S["connessa"] and coll.connesso():
            reti.allinea_secrets(*S["connessa"])
        else:
            reti.svuota_secrets()
    mostra([ui.tronca('"{}"'.format(ssid), 270), "eliminata"], ui.OK, "MENU")


def schermata_conferma_reimporta(ev):
    ui.titolo("Reimporta reti")
    ui.pannello(20, 50, ui.W - 40, 120)
    ui.centrato("Le reti salvate sul badge", 66)
    ui.centrato("verranno sostituite da quelle", 84)
    ui.centrato("del file multi_secrets.py", 102)
    ui.pulsanti(136, ["No", "Si, reimporta"], S["sel"], 100, 116)
    ui.piede("A/C scegli   B conferma")
    if BUTTON_A in ev or BUTTON_C in ev:
        S["sel"] = 1 - S["sel"]
    if BUTTON_B in ev:
        if S["sel"] == 0:
            vai("MENU")
            return
        global note
        nuove = reti.reimporta()
        if nuove is None:
            mostra(["multi_secrets.py assente", "o illeggibile: niente cambia"], ui.ERR, "MENU")
        else:
            note = nuove
            mostra(["Reti importate: {}".format(len(note))], ui.OK, "MENU")


def schermata_messaggio(ev):
    righe, colore, poi = S["messaggio"]
    ui.titolo("WiFi Config")
    ui.pannello(16, 70, ui.W - 32, 30 + 18 * len(righe))
    for i, r in enumerate(righe):
        ui.centrato(r, 86 + 18 * i, colore if i == 0 else ui.TXT)
    ui.piede("B: continua")
    if BUTTON_B in ev:
        vai(poi)


def schermata_non_connesso(_ev):
    ui.titolo("WiFi Config")
    ui.pannello(10, 60, ui.W - 20, 70, 8)
    ui.pallino(30, 95, ui.ERR)
    ui.centrato("WiFi non connesso", 80)
    ui.centrato("Riapri WiFi Config per riprovare", 102, ui.DIM)
    ui.piede("HOME: torna al menu")


SCHERMATE = {
    "AVVISO": schermata_avviso,
    "DANNEGGIATO": schermata_danneggiato,
    "PROVA_NOTE": schermata_prova_note,
    "NESSUNA": schermata_nessuna,
    "SCANSIONE": schermata_scansione,
    "ELENCO": schermata_elenco,
    "TASTIERA": schermata_tastiera,
    "PROVA_NUOVA": schermata_prova_nuova,
    "MENU": schermata_menu,
    "SCEGLI_NOTA": schermata_scegli_nota,
    "PROVA_CAMBIO": schermata_prova_cambio,
    "RITORNO": schermata_ritorno,
    "CONFERMA_ELIMINA": schermata_conferma_elimina,
    "CONFERMA_REIMPORTA": schermata_conferma_reimporta,
    "MESSAGGIO": schermata_messaggio,
    "NON_CONNESSO": schermata_non_connesso,
}


# tasti che si ripetono tenendoli premuti, per schermata (None = tutti)
SU_GIU = (BUTTON_UP, BUTTON_DOWN)
RIPETIZIONE = {"TASTIERA": None, "ELENCO": SU_GIU, "SCEGLI_NOTA": SU_GIU,
               "MENU": SU_GIU, "NESSUNA": SU_GIU}


def update():
    ui.sfondo()
    ev = rip.tasti(badge.pressed(), badge.held(), badge.ticks,
                   RIPETIZIONE.get(S["schermata"], ()))
    SCHERMATE[S["schermata"]](ev)


S["sel_elenco"] = 0
if reti.avviso_file_system():
    vai("AVVISO")
else:
    inizia()

run(update)
