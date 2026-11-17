# -*- coding: utf-8 -*-
"""Quelle: Karriereportal des Landes Berlin.

Die zweitgrößte Einzelquelle nach Interamt. Das Portal bündelt die
Senatsverwaltungen, die zwölf Bezirksämter, Polizei, Feuerwehr und die
nachgeordneten Behörden — am 12.11.2026 waren es **629 Stellen**.

Warum eine eigene Quelle und nicht einfach eine Arbeitgeberseite? Weil die
Übersichtsseite nur die ersten rund 15 Stellen zeigt. Als eine von 93
Karriereseiten behandelt brachte das Portal genau einen Treffer — bei 629
ausgeschriebenen Stellen.

Die gute Nachricht: Es blättert über einen schlichten Parameter in der Adresse
(`?start=0`, `?start=20`, …) und braucht dafür **keinen Browser**. Auch die
Detailseiten haben feste Adressen und lassen sich über HTTP abrufen.
"""

import re
import time
from urllib.parse import urljoin

from einordnung import GESCHLECHT_RE, aufraeumen, ist_menuetext

UEBERSICHT = "https://www.karriereportal-stellen.berlin.de/stellenangebote.html"
ZAEHLSEITE = "https://www.berlin.de/karriereportal/stellensuche/"
BASIS = "https://www.karriereportal-stellen.berlin.de/"

SEITENGROESSE = 20          # so viele Einträge springt der Parameter weiter
PAUSE = 0.35                # Rücksicht zwischen den Seitenabrufen


def gesamtzahl():
    """Wie viele Stellen schreibt das Land gerade aus? Das Portal sagt es selbst."""
    from scrapling.fetchers import Fetcher
    try:
        antwort = Fetcher.get(ZAEHLSEITE, timeout=20, stealthy_headers=True,
                              follow_redirects=True)
        text = antwort.get_all_text(ignore_tags=("script", "style", "noscript")) or ""
    except Exception:
        return None
    treffer = re.search(r"([\d.]+)\s*Stellen", text)
    if not treffer:
        return None
    try:
        return int(treffer.group(1).replace(".", ""))
    except ValueError:
        return None


def _seite_lesen(start):
    """Eine Übersichtsseite abrufen und die Ausschreibungen herausziehen."""
    from scrapling.fetchers import Fetcher
    antwort = Fetcher.get(f"{UEBERSICHT}?start={int(start)}", timeout=25,
                          stealthy_headers=True, follow_redirects=True, retries=2)
    if antwort.status >= 400:
        raise RuntimeError(f"HTTP {antwort.status}")

    gefunden = []
    for element in antwort.css("a"):
        href = element.attrib.get("href") or ""
        if not href:
            continue
        ziel = urljoin(BASIS, href)
        # Die Blätter-Links zeigen auf die Übersicht selbst
        if not ziel.startswith(BASIS) or "/stellenangebote.html" in ziel:
            continue
        titel = aufraeumen(element.get_all_text() or "")
        if not titel or len(titel) < 10 or ist_menuetext(titel):
            continue
        # Das Geschlechtskürzel ist auch hier das verlässlichste Signal
        if not GESCHLECHT_RE.search(titel):
            continue
        gefunden.append({"titel": titel, "url": ziel})
    return gefunden


def trefferliste_holen(seiten=32, melden=None):
    """Blättert durch das Portal und gibt die Ausschreibungen zurück.

    seiten  Wie viele Übersichtsseiten gelesen werden. 32 Seiten × 20 Einträge
            decken die rund 630 Stellen vollständig ab.
    """
    def sagen(was):
        if melden:
            melden(was)

    gesamt = gesamtzahl()
    sagen(f"Karriereportal Berlin: {gesamt or '?'} Stellen ausgeschrieben")

    datensaetze, gesehen = [], set()
    leere_seiten = 0
    for nummer in range(seiten):
        start = nummer * SEITENGROESSE
        try:
            treffer = _seite_lesen(start)
        except Exception as fehler:
            sagen(f"Karriereportal Berlin: Seite {nummer + 1} nicht lesbar "
                  f"({type(fehler).__name__})")
            break

        neu = 0
        for satz in treffer:
            if satz["url"] in gesehen:
                continue
            gesehen.add(satz["url"])
            satz.update(quelle="Karriereportal Berlin", arbeitgeber="Land Berlin",
                        sektor="oed_be", region="Berlin", ort="Berlin")
            datensaetze.append(satz)
            neu += 1

        if neu == 0:
            # Zwei leere Seiten hintereinander heißt: Ende erreicht
            leere_seiten += 1
            if leere_seiten >= 2:
                break
        else:
            leere_seiten = 0

        if (nummer + 1) % 5 == 0 or nummer + 1 == seiten:
            sagen(f"Karriereportal Berlin: {len(datensaetze)} Stellen gelesen "
                  f"(Seite {nummer + 1})")
        time.sleep(PAUSE)

    sagen(f"Karriereportal Berlin: {len(datensaetze)} Stellen in der Liste")
    return datensaetze


# Der Arbeitgeber steht nicht in der Übersicht, aber meist im Detailtext.
BEHOERDE_RE = re.compile(
    r"\b((?:Senatsverwaltung für [\wäöüß\-, ]{3,60}"
    r"|Bezirksamt [\wäöüß\-]+(?: von Berlin)?"
    r"|Landesamt für [\wäöüß\-, ]{3,50}"
    r"|Polizei Berlin|Berliner Feuerwehr|Berliner Verwaltungsakademie"
    r"|Senatskanzlei|Abgeordnetenhaus von Berlin))")


def arbeitgeber_finden(text, rueckfall="Land Berlin"):
    """Zieht die ausschreibende Behörde aus dem Detailtext."""
    treffer = BEHOERDE_RE.search(text or "")
    if treffer:
        name = " ".join(treffer.group(1).split())
        return name[:80].rstrip(" ,-")
    return rueckfall


def volltext_holen(url, pause=0.3):
    """Ausschreibungstext einer Detailseite. Ohne Browser."""
    from scrapling.fetchers import Fetcher
    antwort = Fetcher.get(url, timeout=25, stealthy_headers=True,
                          follow_redirects=True, retries=2)
    if antwort.status >= 400:
        raise RuntimeError(f"HTTP {antwort.status}")
    text = antwort.get_all_text(ignore_tags=("script", "style", "noscript")) or ""
    time.sleep(pause)
    return _saeubern(text)


_RAHMEN = [
    r"Zur Navigation springen", r"Zum Inhalt springen", r"Barrierefrei",
    r"Leichte Sprache", r"Gebärdensprache", r"Karriereportal",
    r"Diese Website verwendet Cookies.*", r"Cookie-Einstellungen",
    r"Datenschutzerklärung", r"Impressum", r"Inhaltsverzeichnis",
]


def _saeubern(text):
    for muster in _RAHMEN:
        text = re.sub(muster, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    seiten = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    treffer = trefferliste_holen(seiten=seiten, melden=lambda w: print(" ·", w))
    print(f"\n{len(treffer)} Stellen\n")
    for satz in treffer[:20]:
        print(f"  {satz['titel'][:76]}")
