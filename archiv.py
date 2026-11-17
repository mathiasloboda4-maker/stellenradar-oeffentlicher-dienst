# -*- coding: utf-8 -*-
"""Archiviert die Ausschreibungsseite als PDF.

Der Grund ist unangenehm praktisch: Fast alle Portale nehmen eine Ausschreibung
offline, sobald die Frist durch ist — oft ohne Vorwarnung und ohne dass man
weiß, wann genau. Danach ist nicht mehr nachvollziehbar, worauf man sich
beworben hat. Deshalb legt der Stellenradar zu jeder gefundenen Stelle
automatisch eine PDF-Kopie der Seite an.

Zwei Dokumente je Stelle, beide bleiben dauerhaft liegen:

  Archiv-PDF    die Originalseite, wie sie im Browser aussieht
  Steckbrief    die aufbereiteten Eckdaten plus Volltext (siehe steckbrief.py)

Gelöscht wird nichts von selbst — auch dann nicht, wenn die Stelle verworfen
wird. Nur über „Archiv aufräumen" in der Oberfläche.
"""

import os
import re
import shutil
import subprocess
import tempfile
from datetime import date, datetime

import datenbank as db
from steckbrief import PdfFehler, browser_finden, _metadaten_setzen

ARCHIV_ORDNER = os.path.join(os.path.dirname(db.DB_PFAD), "archiv")

# Chrome braucht Zeit: Die Seite muss laden, JavaScript laufen, Schriften da sein.
WARTEN_MS = 4000
ZEITLIMIT_S = 90


def ordner():
    os.makedirs(ARCHIV_ORDNER, exist_ok=True)
    return ARCHIV_ORDNER


def _dateiname(zeile):
    def sauber(text, grenze):
        text = re.sub(r"[^\wäöüÄÖÜß\- ]", "", str(text or ""))
        return re.sub(r"\s+", "-", text.strip())[:grenze].strip("-")
    teile = [date.today().isoformat(),
             sauber(zeile["arbeitgeber"], 32) or "Arbeitgeber",
             sauber(zeile["titel"], 52) or "Stelle"]
    return "_".join(t for t in teile if t) + "_Originalseite.pdf"


def seite_sichern(url, zielpfad, titel="", thema=""):
    """Druckt eine Webseite mit Chrome im Hintergrund in eine PDF-Datei.

    Zwei bekannte Stolperfallen, beide schon einmal Zeit gekostet:
      · Chrome braucht eine ausdrückliche Adresse, hier die echte http(s)-URL.
      · Enthält der ZIELPFAD ein Leerzeichen, schreibt Chrome stillschweigend
        nichts — und Windows-Benutzerordner enthalten oft eines („Max
        Mustermann"). Deshalb wird immer in einen Temp-Ordner gedruckt (dort
        gilt der 8.3-Kurzname ohne Leerzeichen) und die fertige Datei danach
        an ihren Platz kopiert.
    """
    browser = browser_finden()
    if not browser:
        raise PdfFehler("Kein Chrome oder Edge gefunden — ohne einen von beiden "
                        "lässt sich keine Seite archivieren.")
    if not re.match(r"^https?://", url or "", re.IGNORECASE):
        raise PdfFehler(f"Keine abrufbare Adresse: {url!r}")

    arbeitsordner = tempfile.mkdtemp(prefix="radar_archiv_")
    zwischen = os.path.join(arbeitsordner, "seite.pdf")
    befehl = [
        browser, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--no-pdf-header-footer", "--print-to-pdf-no-header",
        "--hide-scrollbars", "--disable-extensions",
        f"--virtual-time-budget={WARTEN_MS}",
        f"--print-to-pdf={zwischen}", url,
    ]
    try:
        ergebnis = subprocess.run(befehl, capture_output=True, timeout=ZEITLIMIT_S)
    except subprocess.TimeoutExpired as fehler:
        shutil.rmtree(arbeitsordner, ignore_errors=True)
        raise PdfFehler("Die Seite hat zu lange gebraucht.") from fehler

    if not os.path.exists(zwischen) or os.path.getsize(zwischen) < 1200:
        meldung = (ergebnis.stderr or b"").decode("utf-8", "ignore")[-200:]
        shutil.rmtree(arbeitsordner, ignore_errors=True)
        raise PdfFehler(f"Chrome hat keine brauchbare Seite geliefert. {meldung}".strip())

    os.makedirs(os.path.dirname(zielpfad), exist_ok=True)
    shutil.copy2(zwischen, zielpfad)
    shutil.rmtree(arbeitsordner, ignore_errors=True)
    _metadaten_setzen(zielpfad, titel or url,
                      thema or f"Archivierte Ausschreibungsseite, abgerufen am "
                               f"{datetime.now().strftime('%d.%m.%Y')}. Quelle: {url}")
    return zielpfad


def stelle_archivieren(kennung, ueberschreiben=False):
    """Archiviert die Originalseite einer Stelle. Gibt den Pfad zurück."""
    zeile = db.eine(kennung)
    if not zeile:
        raise PdfFehler(f"Stelle {kennung} gibt es nicht.")

    vorhanden = zeile["archiv_pdf"] if "archiv_pdf" in zeile.keys() else None
    if vorhanden and os.path.exists(vorhanden) and not ueberschreiben:
        return vorhanden

    ziel = os.path.join(ordner(), _dateiname(zeile))
    seite_sichern(zeile["url"], ziel,
                  titel=f"{zeile['titel']} — {zeile['arbeitgeber'] or ''}".strip(" —"))
    db.archiv_merken(kennung, ziel)
    return ziel


def fehlende_archivieren(kennungen=None, melden=None, ueberschreiben=False):
    """Archiviert alles, was noch keine Kopie hat.

    Läuft nach dem Suchlauf. Gibt (gesichert, uebersprungen, fehler) zurück."""
    def sagen(text):
        if melden:
            melden(text)

    if kennungen is None:
        zeilen = [z for z in db.holen(status=[db.NEU, db.VORGEMERKT, db.BEWORBEN])
                  if ueberschreiben or not _hat_archiv(z)]
        kennungen = [z["id"] for z in zeilen]

    gesichert, uebersprungen, fehler = [], 0, []
    gesamt = len(kennungen)
    for nummer, kennung in enumerate(kennungen, 1):
        zeile = db.eine(kennung)
        if not zeile:
            continue
        if not ueberschreiben and _hat_archiv(zeile):
            uebersprungen += 1
            continue
        sagen(f"Archiviere ({nummer}/{gesamt}): {zeile['titel'][:52]}")
        try:
            pfad = stelle_archivieren(kennung, ueberschreiben=ueberschreiben)
            gesichert.append(pfad)
        except Exception as ausnahme:
            fehler.append(f"{zeile['titel'][:44]}: {ausnahme}")
    sagen(f"Archiv: {len(gesichert)} Seiten gesichert, {uebersprungen} schon vorhanden, "
          f"{len(fehler)} nicht erreichbar.")
    return gesichert, uebersprungen, fehler


def _hat_archiv(zeile):
    try:
        pfad = zeile["archiv_pdf"]
    except (KeyError, IndexError):
        return False
    return bool(pfad) and os.path.exists(pfad)


def uebersicht():
    """Was liegt im Archiv? Für die Oberfläche."""
    os.makedirs(ARCHIV_ORDNER, exist_ok=True)
    dateien = [f for f in os.listdir(ARCHIV_ORDNER) if f.lower().endswith(".pdf")]
    groesse = sum(os.path.getsize(os.path.join(ARCHIV_ORDNER, f)) for f in dateien)
    mit_eintrag = 0
    verwaist = []
    bekannt = set()
    with db.verbinden() as v:
        for zeile in v.execute("SELECT archiv_pdf FROM stellen "
                               "WHERE archiv_pdf IS NOT NULL AND archiv_pdf != ''"):
            bekannt.add(os.path.basename(zeile["archiv_pdf"]))
    for name in dateien:
        if name in bekannt:
            mit_eintrag += 1
        else:
            verwaist.append(name)
    return {"ordner": ARCHIV_ORDNER, "anzahl": len(dateien),
            "groesse_mb": groesse / 1024 / 1024, "zugeordnet": mit_eintrag,
            "verwaist": verwaist}


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    db.einrichten()
    if "--alle" in sys.argv:
        fehlende_archivieren(melden=print)
    info = uebersicht()
    print(f"\nArchiv: {info['anzahl']} PDFs, {info['groesse_mb']:.1f} MB")
    print(f"  Ordner: {info['ordner']}")
    print(f"  einer Stelle zugeordnet: {info['zugeordnet']}")
    if info["verwaist"]:
        print(f"  ohne Stelle in der Liste: {len(info['verwaist'])}")
