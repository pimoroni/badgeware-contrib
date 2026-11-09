# Testi dell'interfaccia in piu' lingue.
#
# Ogni lingua e' un file lang/<codice>.json con le stesse chiavi di
# lang/en.json (piu' "_name", il nome della lingua nel menu). Per aggiungere
# una lingua basta aggiungere il file: compare da sola nel selettore. Una
# chiave mancante usa il testo inglese, quindi un file parziale funziona.
# Nessuna dipendenza dalle API Badgeware (gira anche in CPython per i test).

import json
import os

PREDEFINITA = "en"

_base = {}
_testi = {}
_codice = PREDEFINITA


def _leggi(percorso):
    try:
        with open(percorso) as f:
            dati = json.loads(f.read())
    except (OSError, ValueError):
        return {}
    return dati if isinstance(dati, dict) else {}


def disponibili(cartella="lang"):
    # -> [(codice, nome)] ordinati per codice, inglese sempre presente
    try:
        nomi = os.listdir(cartella)
    except OSError:
        nomi = []
    out = []
    for n in sorted(nomi):
        if n.endswith(".json"):
            codice = n[:-5]
            out.append((codice, _leggi(cartella + "/" + n).get("_name", codice)))
    if not any(c == PREDEFINITA for c, _ in out):
        out.insert(0, (PREDEFINITA, "English"))
    return out


def carica(codice, cartella="lang"):
    # -> codice effettivamente caricato (l'inglese se il file non c'e')
    global _base, _testi, _codice
    _base = _leggi(cartella + "/" + PREDEFINITA + ".json")
    _testi = _base if codice == PREDEFINITA else _leggi(cartella + "/" + codice + ".json")
    if not _testi:
        _testi = _base
        codice = PREDEFINITA
    _codice = codice
    return codice


def attuale():
    return _codice


def t(chiave, *args):
    # non solleva mai eccezioni: chiave mancante -> inglese -> la chiave stessa
    s = _testi.get(chiave) or _base.get(chiave) or chiave
    if not args:
        return s
    try:
        return s % args
    except (TypeError, ValueError):
        return s
