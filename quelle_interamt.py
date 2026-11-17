# -*- coding: utf-8 -*-
"""Quelle: INTERAMT — das gemeinsame Stellenportal des öffentlichen Dienstes.

Die wertvollste Einzelquelle des Radars. Eine Umkreissuche um Potsdam (PLZ 14467)
erfasst Berlin und Potsdam samt Umgebung in einem Durchgang und liefert pro
Stelle schon in der Trefferliste: Behörde, Bezeichnung, Besoldung, Entgelt,
PLZ/Ort, Entfernung in km, Dienstort, Einstelldatum und Bewerbungsfrist.

Zwei Befunde aus der Erkundung, die den Ablauf bestimmen:

  1. Die Suche ist eine Apache-Wicket-Anwendung. Der Suchknopf lässt sich nicht
     zuverlässig anklicken; Enter im PLZ-Feld schickt die Suche ab.
  2. Die Trefferliste blättert nicht, sie lädt nach: Knopf „mehr laden" hängt
     je Klick 20 weitere Zeilen an dieselbe Tabelle.

Detailseiten haben eine feste Adresse (…/koop/app/stelle?id=NUMMER) und lassen
sich ohne Browser abrufen. Deshalb: Liste einmal im Browser, Details über HTTP.
"""

import re
import time

START_URL = "https://www.interamt.de/"
DETAIL_URL = "https://interamt.de/koop/app/stelle?id={}"

# Reihenfolge der Tabellenspalten, wie am 11.11.2026 vorgefunden.
SPALTEN = ["id", "behoerde", "titel", "besoldung", "entgelt", "plz_ort",
           "entfernung", "dienstort", "eingestellt", "frist"]

# Zeilen als JSON aus der Seite holen. Im Browser auszulesen ist robuster als
# über Selektoren von außen, weil innerText die Zellen schon aufgeräumt liefert.
ZEILEN_JS = """
() => Array.from(document.querySelectorAll('tbody tr')).map(tr =>
    Array.from(tr.querySelectorAll('td')).map(td => (td.innerText || '').trim())
).filter(z => z.length >= 10)
"""

# Der Cookie-Hinweis klebt am Seitenende und verdeckt genau den Knopf „mehr
# laden" — ohne Schließen bricht jeder Klick mit Zeitüberschreitung ab.
# Interamt schreibt selbst: „Wir nutzen auf unserer Website ausschließlich
# notwendige Cookies." Es gibt also keine Auswahl abzulehnen; Bestätigen ist
# hier die datensparsame Antwort. Die sparsameren Beschriftungen stehen
# trotzdem zuerst, falls das Banner einmal umgebaut wird.
COOKIE_KNOEPFE = ["Nur notwendige", "Nur technisch notwendige", "Alle ablehnen",
                  "Cookies akzeptieren"]

# „mehr laden" ist keine eigene Schaltfläche, sondern eine Beschriftung darin.
MEHR_LADEN = "button:has(span.ia-e-button__label:text-is('mehr laden'))"

# Gemessen am 11.11.2026: Die Trefferliste zeigt 10 Stellen je Schub. Im DOM
# stehen 20 `tbody tr`, aber nur 10 sind Datenzeilen mit zehn Zellen — die
# übrigen gehören zu einer zweiten Tabelle auf derselben Seite.
SEITENGROESSE = 10


ZEILEN_ZAEHLEN_JS = """
() => Array.from(document.querySelectorAll('tbody tr'))
        .filter(tr => tr.querySelectorAll('td').length >= 10).length
"""


def gesamtzahl_lesen(seite):
    """'826 Angebote gefunden' — die Seite nennt ihre Trefferzahl selbst.
    Damit wissen wir, worauf zu warten ist, statt blind zu pausieren."""
    try:
        text = seite.evaluate("() => document.body.innerText || ''")
    except Exception:
        return None
    treffer = re.search(r"([\d.]+)\s*Angebote?\s*(?:gefunden)?", text)
    if not treffer:
        return None
    try:
        return int(treffer.group(1).replace(".", ""))
    except ValueError:
        return None


def _warten_auf_zeilen(seite, soll, grenze_ms=30000):
    """Wartet, bis mindestens `soll` Trefferzeilen im DOM stehen.

    Ein fester Wartewert reichte nicht: Die Tabelle füllt sich in Schüben, und
    zwischen zwei Schüben steht die Zeilenzahl kurz still. Ein Stabilitätstest
    allein brach deshalb bei 10 von 20 Zeilen ab."""
    try:
        seite.wait_for_function(
            "soll => Array.from(document.querySelectorAll('tbody tr'))"
            ".filter(tr => tr.querySelectorAll('td').length >= 10).length >= soll",
            arg=soll, timeout=grenze_ms)
    except Exception:
        pass        # Zeitüberschreitung ist kein Fehler: dann nehmen wir, was da ist
    # Kurz nachlaufen lassen, damit der letzte Schub vollständig ist
    seite.wait_for_timeout(900)
    return seite.evaluate(ZEILEN_JS)


def _banner_schliessen(seite):
    """Schließt den Cookie-Hinweis. Muss vor UND nach der Suche laufen: Das
    Banner steht auf der Trefferliste erneut und verdeckt „mehr laden"."""
    for beschriftung in COOKIE_KNOEPFE:
        try:
            knopf = seite.get_by_role("button", name=beschriftung, exact=False).first
            if knopf.count() and knopf.is_visible(timeout=700):
                knopf.click(timeout=2500)
                seite.wait_for_timeout(800)
                return True
        except Exception:
            continue
    return False


def _mehr_laden(seite):
    """Klickt „mehr laden". Gibt False zurück, wenn es den Knopf nicht mehr gibt.

    Selbstheilend: Das Cookie-Banner erscheint verzögert und legt sich genau
    über diesen Knopf. Der erste Klick läuft dann in eine Zeitüberschreitung.
    Deshalb wird nach einem Fehlschlag das Banner geschlossen und einmal
    wiederholt — das ist der Ablauf, der im Versuch zuverlässig funktioniert
    hat."""
    try:
        knopf = seite.locator(MEHR_LADEN).first
        if knopf.count() == 0 or not knopf.is_visible(timeout=1500):
            return False
    except Exception:
        return False

    for versuch in (1, 2):
        try:
            knopf.scroll_into_view_if_needed(timeout=3000)
            seite.wait_for_timeout(250)
            knopf.click(timeout=5000)
            return True
        except Exception:
            if versuch == 1:
                _banner_schliessen(seite)
                continue
            # Zweiter Fehlschlag: notfalls das Klickereignis direkt auslösen
            try:
                knopf.dispatch_event("click")
                seite.wait_for_timeout(300)
                return True
            except Exception:
                return False
    return False


def _datum(text):
    """'02.12.2026' -> '2026-12-02'. Alles andere wird zu None."""
    treffer = re.match(r"\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\s*$", text or "")
    if not treffer:
        return None
    tag, monat, jahr = (int(g) for g in treffer.groups())
    try:
        from datetime import date
        return date(jahr, monat, tag).isoformat()
    except ValueError:
        return None


def _km(text):
    treffer = re.search(r"(\d+)\s*km", text or "", re.IGNORECASE)
    return int(treffer.group(1)) if treffer else None


def _entgelt(besoldung, entgelt):
    """Macht aus 'TVöD-Bund E 12' ein 'E 12' und aus 'A9g - A11' ein 'A 11'.
    Bei Spannen wird die obere Gruppe genommen, die ist für die Einordnung
    aussagekräftiger.

    Unplausible Gruppen (etwa „E 17", das es im TVöD nicht gibt) werden
    verworfen — `einordnung.entgelt_pruefen` kennt die Obergrenzen.
    """
    from einordnung import entgelt_pruefen
    for rohtext in (entgelt or "", besoldung or ""):
        gruppen = re.findall(r"\b([AB])\s?(\d{1,2})[a-z]?\b", rohtext)
        if gruppen:
            buchstabe, nummer = gruppen[-1]
            geprueft = entgelt_pruefen(f"{buchstabe}{int(nummer)}")
            if geprueft:
                return geprueft
        gruppen = re.findall(r"\bE\s?(\d{1,2})[a-z]?\b", rohtext, re.IGNORECASE)
        if gruppen:
            geprueft = entgelt_pruefen(f"E{int(gruppen[-1])}")
            if geprueft:
                return geprueft
    return None


def _ort(plz_ort):
    """'10117 Berlin' -> ('10117', 'Berlin')"""
    treffer = re.match(r"\s*(\d{5})\s+(.+?)\s*$", plz_ort or "")
    if treffer:
        return treffer.group(1), treffer.group(2)
    return None, (plz_ort or "").strip() or None


def _region_aus_plz(plz, ort):
    """Ordnet die Postleitzahl einer Region zu — steuert die Passungs-Punkte."""
    ort = (ort or "")
    if plz:
        nummer = int(plz)
        if 14467 <= nummer <= 14482:
            return "Babelsberg" if "babelsberg" in ort.lower() else "Potsdam"
        if 14400 <= nummer <= 14559:
            return "Potsdam-Mittelmark"
        if 10000 <= nummer <= 14199:
            return "Berlin"
        if 14600 <= nummer <= 16999 or 3000 <= nummer <= 3999:
            return "Brandenburg"
    if "potsdam" in ort.lower():
        return "Potsdam"
    if "berlin" in ort.lower():
        return "Berlin"
    return "Sonstige"


def _sektor_aus_behoerde(behoerde):
    """Grobe Zuordnung aus dem Behördennamen. Interamt mischt Bund, Länder,
    Kommunen und einzelne Vereine, deshalb lohnt die Unterscheidung."""
    text = (behoerde or "").lower()
    if re.search(r"bundes|bmi\b|bundesministerium|bundesamt|bundesanstalt|"
                 r"deutsche rentenversicherung|bundesagentur|auswärtige", text):
        return "oed_bund"
    if re.search(r"universit|hochschule|fachhochschule|institut für|leibniz|"
                 r"helmholtz|max-planck|fraunhofer|akademie der wissenschaft", text):
        return "wissenschaft"
    if re.search(r"\bberlin\b|senatsverwaltung|bezirksamt", text):
        return "oed_be"
    return "oed_bb"


def zeile_umwandeln(zellen):
    """Macht aus einer Tabellenzeile einen Datensatz."""
    werte = dict(zip(SPALTEN, [z.strip() for z in zellen]))
    # In der ID-Zelle steht zusätzlich der Linktext "Stellenausschreibung öffnen"
    kennung = re.search(r"\b(\d{5,9})\b", werte.get("id", ""))
    if not kennung:
        return None
    nummer = kennung.group(1)
    plz, ort = _ort(werte.get("plz_ort"))
    titel = " ".join((werte.get("titel") or "").split())
    if not titel:
        return None
    behoerde = " ".join((werte.get("behoerde") or "").split())
    return {
        "quelle": "Interamt",
        "interamt_id": nummer,
        "url": DETAIL_URL.format(nummer),
        "titel": titel,
        "arbeitgeber": behoerde or "unbekannt",
        "entgelt": _entgelt(werte.get("besoldung"), werte.get("entgelt")),
        "plz": plz,
        "ort": ort,
        "entfernung_km": _km(werte.get("entfernung")),
        "dienstort_art": " ".join((werte.get("dienstort") or "").split()) or None,
        "eingestellt": _datum(werte.get("eingestellt")),
        "frist": _datum(werte.get("frist")),
        "region": _region_aus_plz(plz, ort),
        "sektor": _sektor_aus_behoerde(behoerde),
    }


def trefferliste_holen(plz="14467", nachladen=20, max_km=70, melden=None):
    """Fährt die Umkreissuche und gibt die Rohzeilen zurück.

    nachladen  Wie oft „mehr laden" geklickt wird. Je Klick kommen 10 Zeilen
               dazu. Die Liste ist nach Einstelldatum absteigend sortiert, es
               kommen also immer die neuesten zuerst. 25 Klicks ≈ 260 Stellen.
    max_km     Stellen weiter weg werden verworfen.
    """
    def sagen(was):
        if melden:
            melden(was)

    gesammelt = []

    def aktion(seite):
        _banner_schliessen(seite)

        feld = seite.locator("input[name='PLZ']").first
        feld.fill(plz)
        seite.wait_for_timeout(300)
        feld.press("Enter")            # der Suchknopf reagiert nicht zuverlässig
        try:
            seite.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        # Nach der Suche steht das Banner wieder da und verdeckt „mehr laden".
        _banner_schliessen(seite)

        # Die Seite nennt ihre Trefferzahl selbst.
        gesamt = gesamtzahl_lesen(seite)
        zeilen = _warten_auf_zeilen(seite, min(SEITENGROESSE, gesamt or SEITENGROESSE))
        sagen(f"Interamt: {len(zeilen)} von {gesamt or '?'} Stellen geladen")

        for runde in range(nachladen):
            vorher = len(zeilen)
            if gesamt and vorher >= gesamt:
                break
            if not _mehr_laden(seite):
                break
            zeilen = _warten_auf_zeilen(
                seite, min(vorher + SEITENGROESSE, gesamt or vorher + SEITENGROESSE),
                grenze_ms=20000)
            if len(zeilen) <= vorher:
                break                  # nichts mehr nachgekommen
            sagen(f"Interamt: {len(zeilen)} von {gesamt or '?'} Stellen geladen "
                  f"(Nachladen {runde + 1}/{nachladen})")

        gesammelt.extend(zeilen)
        return seite

    from scrapling.fetchers import StealthyFetcher
    sagen("Interamt: Umkreissuche wird gestartet …")
    StealthyFetcher.fetch(START_URL, headless=True, network_idle=True,
                          timeout=120000, wait=3000, page_action=aktion,
                          disable_resources=False)

    datensaetze, gesehen = [], set()
    for zellen in gesammelt:
        satz = zeile_umwandeln(zellen)
        if not satz or satz["interamt_id"] in gesehen:
            continue
        gesehen.add(satz["interamt_id"])
        if max_km and satz["entfernung_km"] and satz["entfernung_km"] > max_km:
            continue
        datensaetze.append(satz)
    sagen(f"Interamt: {len(datensaetze)} Stellen im Umkreis von {max_km} km")
    return datensaetze


def volltext_holen(url, pause=0.4):
    """Holt den Ausschreibungstext einer Detailseite. Ohne Browser — die
    Detailseiten liefern ihren Text im HTML."""
    from scrapling.fetchers import Fetcher
    antwort = Fetcher.get(url, timeout=25, stealthy_headers=True,
                          follow_redirects=True, retries=2)
    if antwort.status >= 400:
        raise RuntimeError(f"HTTP {antwort.status}")
    text = antwort.get_all_text(ignore_tags=("script", "style", "noscript"))
    time.sleep(pause)
    return _text_saeubern(text or "")


# Kopf- und Fußbereich von Interamt, der in jedem Volltext steckt und nichts
# über die Stelle sagt.
_RAHMEN = [
    r"canopy\s+canopy", r"Zum Hauptinhalt springen", r"Hochkontrast",
    r"Gebärdensprache", r"Leichte Sprache", r"Informationen für Arbeitgeber",
    r"INTERAMT 2\.0 Beta", r"Login\s+Registrieren\s+Hilfe",
    r"© 2008-\d{4} INTERAMT.*", r"Diese Webseite verwendet Cookies.*",
    r"Notwendige Cookies ermöglichen.*", r"Cookies akzeptieren",
    r"Erklärung zur Barrierefreiheit", r"Nutzungsbedingungen",
    r"Cookie-Einstellungen", r"Inhaltsverzeichnis",
]


def _text_saeubern(text):
    for muster in _RAHMEN:
        text = re.sub(muster, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    runden = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    treffer = trefferliste_holen(nachladen=runden, melden=lambda w: print(" ·", w))
    print(f"\n{len(treffer)} Stellen\n")
    for s in treffer[:25]:
        print(f"  {s['region'][:12]:14} {(s['entgelt'] or '—'):6} "
              f"{str(s['entfernung_km']) + 'km':>6}  Frist {s['frist'] or '—':11} "
              f"{s['arbeitgeber'][:26]:28} {s['titel'][:44]}")
