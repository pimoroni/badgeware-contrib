# reti.py - elenco delle reti WiFi note e file secrets del badge.
#
# Due volumi (vedi docs/wifi-config.md):
#   ROOT   = "/"        LittleFS 1MB, l'UNICO scrivibile dal codice, invisibile da PC
#   SYSTEM = "/system/" FAT 12MB, e' l'unita' E: in disk mode, sola lettura per il codice
#
# /multi_secrets.py (ROOT) e' l'unica fonte di verita'. /system/multi_secrets.py
# serve solo come elenco iniziale: viene importato quando in ROOT non c'e' ancora
# nulla (o con reimporta()), poi ignorato. I file si leggono con exec() e non con
# __import__, cosi' non c'e' cache di sys.modules da svuotare dopo ogni scrittura.
import os

ROOT = "/"
SYSTEM = "/system/"

MULTI = "multi_secrets.py"
SECRETS = "secrets.py"


def _esiste(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _testo(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return None


def _leggi(path):
    """Dizionario delle variabili definite nel file; None se manca o non si
    esegue (troncato, corrotto)."""
    src = _testo(path)
    if src is None:
        return None
    ns = {}
    try:
        exec(src, ns)
    except Exception:  # noqa: BLE001 - a broken multi_secrets.py is reported, never fatal
        return None
    return {k: v for k, v in ns.items() if not k.startswith("__")}


def _scrivi_atomico(path, contenuto):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(contenuto)
    try:
        os.rename(tmp, path)
    except OSError:
        try:
            os.remove(path)
        except OSError:
            pass
        os.rename(tmp, path)


def _lista(dati):
    if not dati:
        return None
    reti = dati.get("NETWORKS")
    if not isinstance(reti, list):
        return None
    # password None/mancante -> "" (rete aperta); SSID non stringa scartato:
    # piu' avanti verrebbe disegnato/misurato e un errore riavvierebbe il badge
    return [{"ssid": n["ssid"], "password": str(n.get("password") or "")} for n in reti
            if isinstance(n, dict) and isinstance(n.get("ssid"), str) and n["ssid"]]


def _da_system():
    """Elenco iniziale: /system/multi_secrets.py + la rete di /system/secrets.py."""
    reti = _lista(_leggi(SYSTEM + MULTI)) or []
    s = _leggi(SYSTEM + SECRETS) or {}
    ssid = s.get("WIFI_SSID")
    if ssid and not any(n["ssid"] == ssid for n in reti):
        reti.append({"ssid": ssid, "password": s.get("WIFI_PASSWORD") or ""})
    return reti


def carica():
    """(reti, stato, n_importate). stato: "ok", "importato", "vuoto", "danneggiato"."""
    path = ROOT + MULTI
    if _esiste(path):
        reti = _lista(_leggi(path))
        if reti is None:
            reti = _lista(_leggi(path + ".bak"))
            if reti is None:
                # mai reimportare da /system qui: farebbe ricomparire reti
                # eliminate. Il file rotto resta com'e' finche' l'utente non agisce.
                return [], "danneggiato", 0
        return reti, "ok", 0

    reti = _da_system()
    if not reti:
        return [], "vuoto", 0
    salva(reti)
    return reti, "importato", len(reti)


def avviso_file_system():
    return _esiste(SYSTEM + MULTI) and _esiste(ROOT + MULTI)


def _serializza(reti):
    righe = [
        "# multi_secrets.py - reti WiFi note, gestito da apps/wifi_config\n",
        "# La prima e' l'ultima rete che ha funzionato.\n",
        "NETWORKS = [\n",
    ]
    for n in reti:
        righe.append("    {!r},\n".format({"ssid": n["ssid"], "password": n["password"]}))
    righe.append("]\n")
    return "".join(righe)


def salva(reti):
    path = ROOT + MULTI
    nuovo = _serializza(reti)
    attuale = _testo(path)
    if attuale == nuovo:
        return
    if attuale is not None and _lista(_leggi(path)) is not None:
        _scrivi_atomico(path + ".bak", attuale)
    _scrivi_atomico(path, nuovo)


def in_cima(reti, ssid, password):
    return [{"ssid": ssid, "password": password}] + [dict(n) for n in reti if n["ssid"] != ssid]


def togli(reti, ssid):
    return [dict(n) for n in reti if n["ssid"] != ssid]


def reimporta():
    """None (e niente cambia) se /system/multi_secrets.py manca o non si legge."""
    if _lista(_leggi(SYSTEM + MULTI)) is None:
        return None
    reti = _da_system()
    salva(reti)
    return reti


def _scrivi_secrets(ssid, password):
    root = _leggi(ROOT + SECRETS)
    system = _leggi(SYSTEM + SECRETS) or {}

    if root is None and system.get("WIFI_SSID") == ssid and system.get("WIFI_PASSWORD") == password:
        return  # /system e' gia' giusto e nessuna copia in root lo oscura

    dati = dict(root or {})
    dati.update(system)
    dati["WIFI_SSID"] = ssid
    dati["WIFI_PASSWORD"] = password
    if dati == root:
        return

    righe = ["# secrets.py - WIFI_SSID/WIFI_PASSWORD gestiti da apps/wifi_config\n"]
    for k, v in dati.items():
        righe.append("{} = {!r}\n".format(k, v))
    _scrivi_atomico(ROOT + SECRETS, "".join(righe))


def allinea_secrets(ssid, password):
    """/secrets.py = chiavi della copia in root, sovrascritte da /system/secrets.py
    (REGION, TIMEZONE... modificati a mano), con la rete indicata."""
    _scrivi_secrets(ssid, password)


def svuota_secrets():
    _scrivi_secrets("", "")


def ssid_secrets():
    for path in (ROOT + SECRETS, SYSTEM + SECRETS):
        d = _leggi(path)
        if d is not None:
            return d.get("WIFI_SSID")
    return None
