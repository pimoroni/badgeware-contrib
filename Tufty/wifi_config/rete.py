# rete.py - collegamento WiFi e scansione, con network.WLAN diretto.
#
# wifi_config NON usa wifi.connect() del firmware: una volta creato wifi.wlan,
# ogni wifi.connect() successiva fa avanzare retry interni che, esauriti,
# chiamano fatal_error() -> riavvio del badge (online/modules/common/wifi.py).
# Qui invece: una sola wlan.connect() per tentativo, poi solo lettura dello
# stato, con un timeout nostro.

# stati del chip CYW43 (network.STAT_*)
_OK = 3
_ESITI = {-3: "password", -2: "non_trovata", -1: "fallita"}


def livello(rssi):
    if rssi >= -55:
        return 4
    if rssi >= -67:
        return 3
    if rssi >= -78:
        return 2
    return 1


def elabora_scansione(grezza, note):
    """Tuple di wlan.scan() -> lista di dict ordinata per segnale, una voce per
    SSID (tenendo il segnale migliore), senza reti nascoste."""
    migliori = {}
    for voce in grezza:
        ssid, rssi, sicurezza = voce[0], voce[3], voce[4]
        if isinstance(ssid, bytes):
            try:
                ssid = ssid.decode("utf-8")
            except Exception:  # noqa: BLE001 - skip networks with an undecodable name
                continue
        if not ssid:
            continue
        if ssid not in migliori or rssi > migliori[ssid]["rssi"]:
            migliori[ssid] = {
                "ssid": ssid,
                "rssi": rssi,
                "livello": livello(rssi),
                "aperta": sicurezza == 0,
                "nota": ssid in note,
            }
    return sorted(migliori.values(), key=lambda r: -r["rssi"])


class Collegamento:
    def __init__(self, network_mod):
        self.wlan = network_mod.WLAN(network_mod.STA_IF)
        self.wlan.active(True)
        self.ssid = None
        self._scadenza = None
        self._errore = False

    def avvia(self, ssid, password, timeout_ms, ora):
        # un'eccezione qui risalirebbe fino a run() -> fatal_error() -> riavvio
        self.ssid = ssid
        self._scadenza = ora + timeout_ms
        self._errore = False
        try:
            self.wlan.disconnect()
            if password:
                self.wlan.connect(ssid, password)
            else:
                self.wlan.connect(ssid)
        except Exception:  # noqa: BLE001 - reported as a failed connection
            self._errore = True

    def _ferma(self, esito):
        # un tentativo fallito o scaduto resta attivo nel chip: va fermato,
        # altrimenti la scansione successiva non trova nulla
        try:
            self.wlan.disconnect()
        except Exception:  # noqa: BLE001 - best effort
            pass
        return esito

    def esito(self, ora):
        """None finche' il tentativo e' in corso, poi "ok", "password",
        "non_trovata" o "fallita" (anche per timeout)."""
        if getattr(self, "_errore", False):
            return self._ferma("fallita")
        if self.wlan.isconnected():
            return "ok"
        stato = self.wlan.status()
        if stato in _ESITI:
            return self._ferma(_ESITI[stato])
        if self._scadenza is not None and ora > self._scadenza:
            return self._ferma("fallita")
        return None

    def connesso(self):
        return self.wlan.isconnected()

    def ip(self):
        try:
            return self.wlan.ifconfig()[0]
        except Exception:  # noqa: BLE001 - no IP yet
            return None

    def scansiona(self):
        return self.wlan.scan()

    def scollega(self):
        try:
            self.wlan.disconnect()
        except Exception:  # noqa: BLE001 - best effort
            pass
        self.ssid = None
