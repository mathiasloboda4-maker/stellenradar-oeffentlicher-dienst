# -*- coding: utf-8 -*-
"""PDF-Steckbriefe zu den gefundenen Stellen.

Zwei Erzeugnisse:

  steckbrief_erzeugen()   ein PDF je Ausschreibung mit allen Angaben und dem
                          vollständigen Ausschreibungstext. Damit bleibt die
                          Stelle lesbar, auch wenn die Seite im Netz längst
                          offline ist — genau der Grund für diese Anforderung.
  dossier_erzeugen()      alle vorgemerkten Stellen in einem Dokument, mit
                          Fristenübersicht vorneweg. Zum Ausdrucken.

Erzeugung über HTML und Chrome im Hintergrund (`--headless=new --print-to-pdf`),
anschließend werden die PDF-Metadaten mit pypdf gesetzt.

Zwei Stolperfallen, beide schon einmal Zeit gekostet:
  · Chrome braucht eine ausdrückliche `file:///`-Adresse mit Schrägstrichen.
  · Enthält der Zielpfad ein Leerzeichen, schreibt Chrome die Datei nicht —
    und Windows-Benutzerordner enthalten oft eines („Max Mustermann").
    Deshalb wird immer in einen Temp-Ordner gerendert (dort gilt der
    8.3-Kurzname ohne Leerzeichen) und die fertige Datei danach kopiert.
"""

import html
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date, datetime

import datenbank as db
import konfiguration as kfg
from einordnung import FELDER, FELD_KURZ, SEKTOREN

# Eigene Farbwelt für die Bewerbungsunterlagen — bewusst kein Hochschul- oder
# Firmen-CI, denn das sind private Unterlagen.
BLAU = "#03305D"
GRUEN = "#6B8E3D"
DGRUEN = "#3F5C25"
HELL = "#F4F7F0"


def _eigner():
    """Der Name aus dem eigenen Profil — für Fußzeilen und PDF-Angaben.

    Steht absichtlich nicht im Code: Wer das Programm benutzt, trägt sich
    im Fenster unter „Berufsfelder" ein, das landet in profil.json.
    """
    return (kfg.profil_laden().get("name") or "").strip() or "Stellenradar"
GRAU = "#595959"
ROT = "#A33A3A"
ORANGE = "#C4761A"

BROWSER_KANDIDATEN = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


class PdfFehler(RuntimeError):
    pass


def browser_finden():
    for pfad in BROWSER_KANDIDATEN:
        if os.path.exists(pfad):
            return pfad
    aus_umgebung = os.environ.get("STELLENRADAR_BROWSER")
    if aus_umgebung and os.path.exists(aus_umgebung):
        return aus_umgebung
    return None


# ----------------------------------------------------------------------------------
# GEMEINSAMES AUSSEHEN
# ----------------------------------------------------------------------------------

STIL = f"""
@page {{ size: A4; margin: 16mm 15mm 14mm 15mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: Calibri, "Segoe UI", Arial, sans-serif; font-size: 10.5pt;
        color: #2D2D2D; margin: 0; line-height: 1.45; }}
h1 {{ font-size: 17pt; color: {BLAU}; margin: 0 0 2mm 0; line-height: 1.25; }}
h2 {{ font-size: 12pt; color: {DGRUEN}; margin: 6mm 0 2mm 0;
      border-bottom: 1.2pt solid {GRUEN}; padding-bottom: 1mm; }}
h3 {{ font-size: 11pt; color: {BLAU}; margin: 4mm 0 1mm 0; }}
.kopf {{ border-left: 3.5mm solid {GRUEN}; padding-left: 5mm; margin-bottom: 5mm; }}
.arbeitgeber {{ font-size: 12pt; color: {DGRUEN}; font-weight: bold; margin: 0 0 1mm 0; }}
.marken {{ margin: 3mm 0 0 0; }}
.marke {{ display: inline-block; font-size: 8.5pt; padding: 1mm 2.6mm;
          border-radius: 2mm; margin: 0 1.6mm 1.6mm 0; font-weight: bold; }}
.m-feld {{ background: {HELL}; color: {DGRUEN}; border: 0.6pt solid {GRUEN}; }}
.m-sektor {{ background: #E8EEF5; color: {BLAU}; border: 0.6pt solid {BLAU}; }}
.m-punkte {{ background: {GRUEN}; color: #fff; }}
.m-frist-rot {{ background: {ROT}; color: #fff; }}
.m-frist-orange {{ background: {ORANGE}; color: #fff; }}
.m-frist-gruen {{ background: {HELL}; color: {DGRUEN}; border: 0.6pt solid {GRUEN}; }}
table.eck {{ width: 100%; border-collapse: collapse; margin: 0 0 4mm 0;
             font-size: 10pt; }}
table.eck td {{ padding: 1.5mm 2mm; border-bottom: 0.4pt solid #DDE3D6;
                vertical-align: top; }}
table.eck td.k {{ width: 34mm; color: {GRAU}; font-weight: bold; }}
.text {{ font-size: 9.8pt; white-space: pre-wrap; text-align: left; }}
.fuss {{ margin-top: 6mm; padding-top: 2mm; border-top: 0.6pt solid #CCC;
         font-size: 8pt; color: {GRAU}; }}
.hinweis {{ background: {HELL}; border-left: 2mm solid {GRUEN}; padding: 2.5mm 3mm;
            font-size: 9pt; margin: 3mm 0; }}
.warnung {{ background: #FAEDED; border-left: 2mm solid {ROT}; padding: 2.5mm 3mm;
            font-size: 9pt; margin: 3mm 0; color: #6D2020; }}
a {{ color: {BLAU}; word-break: break-all; }}
.stelle {{ page-break-inside: avoid; border: 0.6pt solid #DDE3D6; border-radius: 1.5mm;
           padding: 3mm 4mm; margin-bottom: 3.5mm; }}
.stelle .titel {{ font-size: 11pt; font-weight: bold; color: {BLAU}; }}
.stelle .zeile {{ font-size: 9pt; color: {GRAU}; margin-top: 1mm; }}
ul.fristen {{ margin: 1mm 0 0 0; padding-left: 5mm; font-size: 9.5pt; }}
ul.fristen li {{ margin-bottom: 0.8mm; }}
.neu-seite {{ page-break-before: always; }}
"""


def _e(text):
    """Text für HTML entschärfen."""
    return html.escape(str(text if text is not None else ""), quote=True)


def _frist_marke(frist):
    """Fristen-Kennzeichnung mit Farbe und Restlaufzeit."""
    tage = db.tage_bis_frist(frist)
    if tage is None:
        return "m-frist-gruen", "Frist nicht angegeben"
    datum = date.fromisoformat(frist).strftime("%d.%m.%Y")
    if tage < 0:
        return "m-frist-rot", f"Frist abgelaufen ({datum})"
    if tage == 0:
        return "m-frist-rot", f"Frist HEUTE ({datum})"
    if tage == 1:
        return "m-frist-rot", f"Frist morgen ({datum})"
    if tage <= 7:
        return "m-frist-orange", f"Frist in {tage} Tagen ({datum})"
    if tage <= 14:
        return "m-frist-orange", f"Frist in {tage} Tagen ({datum})"
    return "m-frist-gruen", f"Frist in {tage} Tagen ({datum})"


def _datum_de(iso):
    if not iso:
        return None
    try:
        return date.fromisoformat(iso).strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return str(iso)


def _feldnamen(zeile):
    import json
    try:
        nummern = json.loads(zeile["felder"] or "[]")
    except (ValueError, TypeError):
        nummern = []
    if not nummern and zeile["feld_haupt"]:
        nummern = [zeile["feld_haupt"]]
    return [f"{FELD_KURZ.get(n, '')} {FELDER.get(n, '')}".strip() for n in nummern]


# ----------------------------------------------------------------------------------
# EINZELNER STECKBRIEF
# ----------------------------------------------------------------------------------

def _steckbrief_html(zeile):
    frist_klasse, frist_text = _frist_marke(zeile["frist"])
    feldnamen = _feldnamen(zeile)

    marken = [f'<span class="marke m-punkte">{zeile["punkte"]} Passungs-Punkte</span>',
              f'<span class="marke {frist_klasse}">{_e(frist_text)}</span>']
    for name in feldnamen[:3]:
        marken.append(f'<span class="marke m-feld">{_e(name)}</span>')
    if zeile["sektor"]:
        marken.append(f'<span class="marke m-sektor">'
                      f'{_e(SEKTOREN.get(zeile["sektor"], zeile["sektor"]))}</span>')

    eck = [
        ("Bewerbungsfrist", _datum_de(zeile["frist"]) or "nicht angegeben"),
        ("Eintritt", _datum_de(zeile["eintritt"]) if zeile["eintritt"] and
         re.match(r"\d{4}-", str(zeile["eintritt"])) else zeile["eintritt"]),
        ("Entgelt / Besoldung", zeile["entgelt"]),
        ("Umfang", zeile["umfang"]),
        ("Befristung", zeile["befristung"]),
        ("Dienstort", zeile["ort"]),
        ("Entfernung Potsdam", f"{zeile['entfernung_km']} km"
         if zeile["entfernung_km"] is not None else None),
        ("Ansprechperson", zeile["kontakt"]),
        ("Telefon", zeile["telefon"]),
        ("E-Mail", zeile["email"]),
        ("Berufsfelder", ", ".join(feldnamen) if feldnamen else None),
        ("Quelle", zeile["quelle"]),
        ("Gefunden am", _datum_de(zeile["gefunden_am"])),
        ("Status", db.STATUS_NAMEN.get(zeile["status"], zeile["status"])),
    ]
    zeilen_html = "".join(
        f'<tr><td class="k">{_e(k)}</td><td>{_e(w)}</td></tr>'
        for k, w in eck if w)

    volltext = (zeile["volltext"] or "").strip()
    if volltext:
        text_block = f'<h2>Ausschreibungstext</h2><div class="text">{_e(volltext)}</div>'
    else:
        text_block = ('<div class="warnung">Von dieser Seite ließ sich kein '
                      'Ausschreibungstext gewinnen. Bitte dem Link unten folgen — '
                      'dort steht die vollständige Ausschreibung.</div>')

    notiz = (zeile["notiz"] or "").strip()
    notiz_block = (f'<h2>Eigene Notiz</h2><div class="hinweis">{_e(notiz)}</div>'
                   if notiz else "")

    gruende = (zeile["punkte_gruende"] or "").strip()
    gruende_block = (f'<div class="hinweis"><b>Wie die Punkte zustande kommen:</b><br>'
                     f'{_e(gruende)}</div>' if gruende else "")

    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<title>{_e(zeile['titel'])}</title><style>{STIL}</style></head>
<body>
  <div class="kopf">
    <p class="arbeitgeber">{_e(zeile['arbeitgeber'] or 'Arbeitgeber unbekannt')}</p>
    <h1>{_e(zeile['titel'])}</h1>
    <div class="marken">{''.join(marken)}</div>
  </div>

  <h2>Eckdaten</h2>
  <table class="eck">{zeilen_html}</table>
  {gruende_block}
  {notiz_block}
  {text_block}

  <div class="fuss">
    Ausschreibung im Netz: <a href="{_e(zeile['url'])}">{_e(zeile['url'])}</a><br>
    Steckbrief erzeugt vom Stellenradar am
    {datetime.now().strftime('%d.%m.%Y um %H:%M')} ·
    Angaben aus der Ausschreibung übernommen, ohne Gewähr — vor der Bewerbung
    bitte auf der Seite des Arbeitgebers prüfen.
  </div>
</body></html>"""


def _dateiname(zeile):
    def sauber(text, grenze):
        text = re.sub(r"[^\wäöüÄÖÜß\- ]", "", str(text or ""))
        text = re.sub(r"\s+", "-", text.strip())
        return text[:grenze].strip("-")
    teile = [date.today().isoformat(),
             sauber(zeile["arbeitgeber"], 34) or "Arbeitgeber",
             sauber(zeile["titel"], 56) or "Stelle"]
    return "_".join(t for t in teile if t) + ".pdf"


def _nach_pdf(html_text, zielpfad, titel, thema):
    """Rendert HTML nach PDF. Der Umweg über den Temp-Ordner ist nötig, weil
    Chrome bei Leerzeichen im Zielpfad stillschweigend nichts schreibt."""
    browser = browser_finden()
    if not browser:
        raise PdfFehler(
            "Kein Chrome oder Edge gefunden. Für die PDF-Erzeugung wird einer "
            "der beiden gebraucht. Pfad notfalls in der Umgebungsvariablen "
            "STELLENRADAR_BROWSER setzen.")

    arbeitsordner = tempfile.mkdtemp(prefix="radar_pdf_")
    quelle = os.path.join(arbeitsordner, "seite.html")
    zwischen = os.path.join(arbeitsordner, "fertig.pdf")
    with open(quelle, "w", encoding="utf-8") as datei:
        datei.write(html_text)

    adresse = "file:///" + quelle.replace("\\", "/")
    befehl = [browser, "--headless=new", "--disable-gpu", "--no-sandbox",
              "--no-pdf-header-footer", "--print-to-pdf-no-header",
              f"--print-to-pdf={zwischen}", adresse]
    try:
        ergebnis = subprocess.run(befehl, capture_output=True, timeout=150)
    except subprocess.TimeoutExpired as fehler:
        raise PdfFehler("Chrome hat nicht geantwortet (Zeitüberschreitung).") from fehler
    if not os.path.exists(zwischen):
        meldung = (ergebnis.stderr or b"").decode("utf-8", "ignore")[-300:]
        raise PdfFehler(f"Chrome hat kein PDF geschrieben. Meldung: {meldung}")

    os.makedirs(os.path.dirname(zielpfad), exist_ok=True)
    shutil.copy2(zwischen, zielpfad)
    shutil.rmtree(arbeitsordner, ignore_errors=True)
    _metadaten_setzen(zielpfad, titel, thema)
    return zielpfad


def _metadaten_setzen(pfad, titel, thema):
    """PDF-Eigenschaften nachtragen. Scheitert das, bleibt das PDF gültig."""
    try:
        from pypdf import PdfReader, PdfWriter
        leser = PdfReader(pfad)
        schreiber = PdfWriter()
        for seite in leser.pages:
            schreiber.add_page(seite)
        schreiber.add_metadata({
            "/Title": titel[:200],
            "/Subject": thema[:300],
            "/Author": "Stellenradar",
            "/Creator": f"Stellenradar ({_eigner()})",
            "/CreationDate": datetime.now().strftime("D:%Y%m%d%H%M%S"),
        })
        with open(pfad, "wb") as datei:
            schreiber.write(datei)
    except Exception:
        pass


def steckbrief_erzeugen(kennung, ordner=None, ueberschreiben=False):
    """Erzeugt den Steckbrief zu einer Stelle und merkt den Pfad in der Datenbank."""
    zeile = db.eine(kennung)
    if not zeile:
        raise PdfFehler(f"Stelle {kennung} gibt es nicht.")
    ordner = ordner or db.PDF_ORDNER
    ziel = os.path.join(ordner, _dateiname(zeile))
    if os.path.exists(ziel) and not ueberschreiben:
        db.pdf_merken(kennung, ziel)
        return ziel
    _nach_pdf(_steckbrief_html(zeile), ziel,
              titel=f"{zeile['titel']} — {zeile['arbeitgeber'] or ''}".strip(" —"),
              thema=f"Stellenausschreibung, Steckbrief des Stellenradars. "
                    f"Quelle: {zeile['url']}")
    db.pdf_merken(kennung, ziel)
    return ziel


def steckbriefe_erzeugen(kennungen, melden=None, ueberschreiben=False):
    """Mehrere Steckbriefe. Gibt (erzeugt, fehler) zurück."""
    erzeugt, fehler = [], []
    gesamt = len(kennungen)
    for nummer, kennung in enumerate(kennungen, 1):
        try:
            pfad = steckbrief_erzeugen(kennung, ueberschreiben=ueberschreiben)
            erzeugt.append(pfad)
            if melden:
                melden(f"({nummer}/{gesamt}) {os.path.basename(pfad)}")
        except Exception as ausnahme:
            fehler.append(f"Stelle {kennung}: {ausnahme}")
            if melden:
                melden(f"({nummer}/{gesamt}) Fehler: {ausnahme}")
    return erzeugt, fehler


# ----------------------------------------------------------------------------------
# DOSSIER: ALLE VORGEMERKTEN STELLEN IN EINEM DOKUMENT
# ----------------------------------------------------------------------------------

FACH_TITEL = [
    ("abgelaufen", "Frist bereits abgelaufen", ROT),
    ("heute_morgen", "Heute oder morgen fällig", ROT),
    ("woche", "Diese Woche fällig", ORANGE),
    ("zwei_wochen", "In zwei Wochen fällig", ORANGE),
    ("spaeter", "Später", DGRUEN),
    ("ohne", "Ohne Fristangabe", GRAU),
]


def _dossier_html(zeilen, kennzahlen):
    heute = datetime.now().strftime("%d.%m.%Y")

    # Fristenübersicht nur über die Stellen im Dossier
    faecher = {name: [] for name, _, _ in FACH_TITEL}
    for zeile in zeilen:
        tage = db.tage_bis_frist(zeile["frist"])
        if tage is None:
            faecher["ohne"].append(zeile)
        elif tage < 0:
            faecher["abgelaufen"].append(zeile)
        elif tage <= 1:
            faecher["heute_morgen"].append(zeile)
        elif tage <= 7:
            faecher["woche"].append(zeile)
        elif tage <= 14:
            faecher["zwei_wochen"].append(zeile)
        else:
            faecher["spaeter"].append(zeile)

    uebersicht = []
    for name, titel, farbe in FACH_TITEL:
        eintraege = faecher[name]
        if not eintraege:
            continue
        punkte = "".join(
            f"<li><b>{_e(_datum_de(z['frist']) or 'ohne Frist')}</b> — "
            f"{_e(z['titel'][:76])} <i>({_e((z['arbeitgeber'] or '')[:40])})</i></li>"
            for z in eintraege)
        uebersicht.append(
            f'<h3 style="color:{farbe}">{_e(titel)} ({len(eintraege)})</h3>'
            f'<ul class="fristen">{punkte}</ul>')

    karten = []
    for zeile in zeilen:
        frist_klasse, frist_text = _frist_marke(zeile["frist"])
        angaben = " · ".join(filter(None, [
            zeile["entgelt"], zeile["umfang"], zeile["befristung"], zeile["ort"],
            f"{zeile['entfernung_km']} km" if zeile["entfernung_km"] is not None else None,
        ]))
        karten.append(f"""
        <div class="stelle">
          <div class="titel">{_e(zeile['titel'])}</div>
          <div class="zeile"><b>{_e(zeile['arbeitgeber'] or '')}</b>
            {(' · ' + _e(angaben)) if angaben else ''}</div>
          <div class="marken">
            <span class="marke m-punkte">{zeile['punkte']} P</span>
            <span class="marke {frist_klasse}">{_e(frist_text)}</span>
            {''.join(f'<span class="marke m-feld">{_e(n)}</span>'
                     for n in _feldnamen(zeile)[:2])}
          </div>
          <div class="zeile">
            {_e(zeile['kontakt'] or '')}
            {(' · ' + _e(zeile['telefon'])) if zeile['telefon'] else ''}
            {(' · ' + _e(zeile['email'])) if zeile['email'] else ''}
          </div>
          <div class="zeile"><a href="{_e(zeile['url'])}">{_e(zeile['url'][:104])}</a></div>
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<title>Stellen-Dossier</title><style>{STIL}</style></head>
<body>
  <div class="kopf">
    <p class="arbeitgeber">Stellenradar · {html.escape(_eigner())}</p>
    <h1>Stellen-Dossier</h1>
    <div class="marken">
      <span class="marke m-punkte">{len(zeilen)} Stellen</span>
      <span class="marke m-sektor">Stand {heute}</span>
    </div>
  </div>

  <div class="hinweis">
    Alle hier aufgeführten Stellen sind im Stellenradar vorgemerkt oder
    beworben. Die Fristen sind aus den Ausschreibungen übernommen; es gilt
    immer die Angabe auf der Seite des Arbeitgebers.
  </div>

  <h2>Termine und Fristen</h2>
  {''.join(uebersicht) or '<p>Keine Stellen mit Frist im Dossier.</p>'}

  <h2 class="neu-seite">Die Stellen im Einzelnen</h2>
  {''.join(karten)}

  <div class="fuss">
    Erzeugt vom Stellenradar am {datetime.now().strftime('%d.%m.%Y um %H:%M')} ·
    In der Datenbank: {kennzahlen['gesamt']} Stellen insgesamt,
    davon {kennzahlen['status'].get(db.VORGEMERKT, 0)} vorgemerkt und
    {kennzahlen['status'].get(db.BEWORBEN, 0)} beworben.
  </div>
</body></html>"""


def dossier_erzeugen(status=(db.VORGEMERKT, db.BEWORBEN), zielpfad=None):
    """Alle Stellen der genannten Status in einem PDF, Fristen vorneweg."""
    zeilen = db.holen(status=list(status), sortierung="frist")
    if not zeilen:
        raise PdfFehler("Es sind keine Stellen vorgemerkt. Erst Stellen mit "
                        "„⭐ Vormerken\" markieren, dann das Dossier erzeugen.")
    zielpfad = zielpfad or os.path.join(
        db.PDF_ORDNER, f"{date.today().isoformat()}_Stellen-Dossier.pdf")
    _nach_pdf(_dossier_html(zeilen, db.kennzahlen()), zielpfad,
              titel=f"Stellen-Dossier {date.today().strftime('%d.%m.%Y')}",
              thema="Vorgemerkte Stellen mit Fristenübersicht, "
                    "erzeugt vom Stellenradar")
    return zielpfad, len(zeilen)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    db.einrichten()
    if "--dossier" in sys.argv:
        pfad, anzahl = dossier_erzeugen()
        print(f"Dossier mit {anzahl} Stellen: {pfad}")
    else:
        zeilen = db.holen(sortierung="punkte")[:3]
        if not zeilen:
            print("Keine Stellen in der Datenbank. Erst einen Suchlauf starten.")
        for zeile in zeilen:
            print("  ", steckbrief_erzeugen(zeile["id"], ueberschreiben=True))
