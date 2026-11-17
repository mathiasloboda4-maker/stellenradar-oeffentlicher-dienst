# -*- coding: utf-8 -*-
"""Erzeugt die Bildschirmfotos für die README — aus Beispieldaten.

Warum ein eigenes Werkzeug und keine Handaufnahmen: Bilder veralten, und von
Hand aufgenommene zeigen am Ende doch echte Daten. Dieses Skript baut eine
Wegwerf-Datenbank mit erfundenen Ausschreibungen, biegt auch die drei
Profildateien auf einen Temp-Ordner um und fotografiert dann fünf Ansichten.

  **Die echten Daten werden nicht angefasst.** Datenbank, Archiv, Steckbriefe
  und das eigene Profil bleiben unberührt — alles läuft im Temp-Ordner.

Aufruf:

    .venv\\Scripts\\python.exe screenshots_erzeugen.py

Ergebnis: bilder/01-dashboard.png … bilder/05-gewichtung.png

Das Fenster erscheint dabei kurz auf dem Bildschirm. Aufgenommen wird es über
PrintWindow, nicht über den Bildschirminhalt — ein Fenster davor stört also
nicht.
"""
import ctypes
import json
import os
import sys
import tempfile
import time
from ctypes import wintypes
from datetime import date, timedelta

# Scharfe Bilder statt hochskalierter: Das Fenster soll in echten Pixeln
# rechnen, sonst stimmen Fenstermaß und Aufnahme auf Geräten mit
# Anzeigeskalierung nicht überein.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

BASIS = os.path.dirname(os.path.abspath(__file__))
BILDER = os.path.join(BASIS, "bilder")

# ----------------------------------------------------------------------------------
# BEISPIELDATEN
#
# Erfundene Ausschreibungen. Die Arbeitgeber sind echte öffentliche Stellen --
# sie stehen ohnehin im Register -- die Stellentitel sind typische Muster, keine
# echten Ausschreibungen. In der README steht, dass es Beispieldaten sind.
# ----------------------------------------------------------------------------------

HEUTE = date.today()


def tage(n):
    return (HEUTE + timedelta(days=n)).isoformat()


# (titel, arbeitgeber, sektor, ort, region, felder, punkte, frist, status, favorit)
STELLEN = [
    ("Referent:in (m/w/d) Verwaltungsdigitalisierung und OZG-Umsetzung",
     "Ministerium des Innern und für Kommunales Brandenburg", "oed_bb",
     "Potsdam", "Potsdam", [1, 4], 31, tage(2), "neu", 1),
    ("Produktmanager:in (m/w/d) Digitaler Arbeitsplatz, E 13 TV-L",
     "IT-Dienstleistungszentrum Berlin", "oed_be", "Berlin", "Berlin",
     [2, 1], 29, tage(5), "neu", 1),
    ("Projektleitung (m/w/d) Registermodernisierung",
     "Bundesverwaltungsamt", "bund", "Berlin", "Berlin", [3, 1], 26,
     tage(9), "neu", 0),
    ("Anforderungsmanagement (m/w/d) Fachverfahren, A 13",
     "Landeshauptstadt Potsdam", "oed_bb", "Potsdam", "Potsdam", [2, 4],
     25, tage(12), "neu", 0),
    ("Consultant (m/w/d) Public Sector Prozessberatung",
     "PD – Berater der öffentlichen Hand", "beratung", "Berlin", "Berlin",
     [4, 3], 22, tage(18), "neu", 0),
    ("Organisationsentwicklung (m/w/d) im Dezernat Zentrale Dienste",
     "Universität Potsdam", "wissenschaft", "Potsdam", "Potsdam", [4, 6],
     21, tage(24), "neu", 0),
    ("Referent:in (m/w/d) IT-Strategie und Dienstleistersteuerung",
     "Senatsverwaltung für Finanzen Berlin", "oed_be", "Berlin", "Berlin",
     [1, 2], 20, None, "neu", 0),
    ("Prozessmanager:in (m/w/d) Digitalisierung der Leistungsprozesse",
     "Deutsche Rentenversicherung Bund", "bund", "Berlin", "Berlin", [4, 2],
     24, tage(7), "vorgemerkt", 1),
    ("Leitung (m/w/d) Geschäftsstelle Digitalisierung",
     "Bezirksamt Neukölln von Berlin", "oed_be", "Berlin", "Berlin",
     [1, 3], 23, tage(15), "vorgemerkt", 0),
    ("Wissenschaftsmanagement (m/w/d) Forschungsförderung",
     "Hasso-Plattner-Institut", "wissenschaft", "Babelsberg",
     "Potsdam-Babelsberg", [6, 3], 18, tage(30), "vorgemerkt", 0),
    ("Senior Consultant (m/w/d) E-Government",
     "INFORA GmbH", "beratung", "Berlin", "Berlin", [1, 4], 19, tage(21),
     "beworben", 0),
    ("Produktverantwortung (m/w/d) Onlinedienste",
     "Bundesdruckerei GmbH", "bund", "Berlin",
     "Berlin", [2, 1], 21, tage(11), "beworben", 1),
    ("Sachbearbeitung (m/w/d) Beihilfe und Versorgung",
     "Zentraldienst der Polizei Brandenburg", "oed_bb", "Potsdam",
     "Potsdam", [5], 9, tage(-3), "verworfen", 0),
    ("Mitarbeit (m/w/d) im Kundenservice Telefonzentrale",
     "Stadtwerke Potsdam", "privat", "Potsdam", "Potsdam", [5], 7,
     tage(-8), "verworfen", 0),
]

NOTIZEN = {
    8: "Telefonat mit Frau Dr. Keller am 14.: Team wird neu aufgebaut, "
       "Entgeltgruppe verhandelbar. Unterlagen bis Monatsende.",
    9: "Bezirksamt — kurzer Weg, aber Befristung auf zwei Jahre. Nachfragen, "
       "ob Entfristung vorgesehen ist.",
    12: "Beworben am 05., Eingangsbestätigung da. Wiedervorlage gesetzt.",
}

BRIEFING = """① KEY FACTS
- Produktmanager:in Digitaler Arbeitsplatz, E 13 TV-L, unbefristet
- IT-Dienstleistungszentrum Berlin, Dienstort Berlin-Mitte
- Bewerbungsfrist in 5 Tagen · Vollzeit, Teilzeit möglich
- Kennziffer 2026/114, Besetzung zum nächstmöglichen Zeitpunkt

② ANSPRECHPERSONEN
- Fachlich: Leitung Produktmanagement, Telefon 030 90222-xxxx
- Personal: Servicebereich Personalgewinnung, bewerbung@beispiel.de

③ MEINE HINTERLEGTEN KOMPETENZEN
- [IT-Produkt- & Anforderungsmanagement] Backlog-Priorisierung und Roadmaps
  im Behördenkontext
- [Digitalisierung & E-Government] E-Government-Lösungen für eine
  Landesverwaltung im Tagesgeschäft gestaltet

④ WAS DIE STELLE VERLANGT
- Produktverantwortung für den digitalen Arbeitsplatz der Berliner Verwaltung
- Anforderungen der Fachbereiche erheben, priorisieren und in Releases
  überführen
- Steuerung externer Dienstleister, Abstimmung mit dem Datenschutz
- Erfahrung mit agilen Vorgehensmodellen in einer öffentlichen Verwaltung

⑤ WO MEINE KOMPETENZEN PASSEN
- Produktverantwortung im Behördenkontext → fünf Jahre im öffentlichen
  IT-Sektor, zuletzt als Produktmanagerin einer Landesverwaltung
- Dienstleistersteuerung → Steuerung externer Partner inklusive
  Budgetverantwortung
- Agile Vorgehensmodelle in der Verwaltung → User Stories und Roadmaps
  genau dort angewandt, im Bewerberfeld selten

⑥ DER ELEFANT IM RAUM
- Kein Informatikstudium. Dreht sich über die Produktperspektive: gefordert
  ist Steuerung, nicht Entwicklung.
- Ausschreibung nennt ITIL-Kenntnisse, im Profil nicht hinterlegt. Offen
  benennen und die Bereitschaft zur Zertifizierung anbieten.

⑦ ZUM ARBEITGEBER  (Modellwissen, ungeprüft)
- Landeseigener IT-Dienstleister Berlins, Anstalt öffentlichen Rechts
- Betreibt das Landesnetz und zentrale Verfahren für die Verwaltung
- Rund 1.000 Beschäftigte, Standort Berlin-Mitte

⑧ FRAGEN FÜRS GESPRÄCH
- Wie ist das Produktmanagement zu den Fachverfahren abgegrenzt?
- Wer entscheidet am Ende über die Priorisierung im Backlog?
- Wie groß ist der Anteil der Dienstleistersteuerung am Tagesgeschäft?
"""

# Beispielprofil fuer die Bilder. Mustermann ist in Deutschland als Platzhalter
# eindeutig -- niemand haelt das fuer eine echte Person.
DEMO_PROFIL = {
    "name": "Erika Mustermann",
    "abschluss": "Diplom-Verwaltungswirtin",
    "wohnort": "Potsdam",
    "verfuegbar": "ab sofort",
    "werdegang": [
        "2024–heute · Produktmanagerin, Landes-IT-Dienstleister",
        "2021–2024 · Projekt E-Akte, Landesbehörde Brandenburg",
        "2017–2021 · Beraterin, Beratungshaus für die öffentliche Hand",
        "Studium Verwaltungswissenschaft (Diplom-Verwaltungswirtin)",
    ],
    "staerken": [
        "Neun Jahre Berufserfahrung, davon fünf im öffentlichen IT-Sektor.",
        "Ab sofort verfügbar — keine Kündigungsfrist zu überbrücken.",
        "Wohnt am Dienstort, also kurzfristig verfügbar.",
    ],
    "weiterbildungen": [
        "Certified Scrum Product Owner (2025)",
        "Verwaltungsdigitalisierung — Zertifikatskurs (2024)",
    ],
}

DEMO_KOMPETENZEN = {
    "1": ["Produktmanagerin bei einem Landes-IT-Dienstleister: "
          "E-Government-Lösungen im Tagesgeschäft gestaltet.",
          "Projekt E-Akte in einer Landesbehörde: zentraler Baustein des "
          "E-Government-Gesetzes praktisch umgesetzt.",
          "Zwei Stationen in Behörden — Verwaltungskultur, Gremienarbeit "
          "und Haushaltslogik sind vertraut."],
    "2": ["Backlog-Priorisierung und Roadmaps im Behördenkontext — deckt "
          "sich fast wörtlich mit entsprechenden Ausschreibungen.",
          "Agile Arbeit mit User Stories, und zwar in der Verwaltung. Das "
          "ist im Bewerberfeld selten.",
          "Bedarfe erhoben, Anforderungen gemanagt, Pilotprojekte bis zum "
          "Proof of Concept begleitet."],
    "3": ["Projekt E-Akte geplant und durchgeführt, inklusive "
          "Prozesserhebung und Change-Konzept.",
          "Steuerung mehrerer externer Partner mit Budgetverantwortung."],
    "4": ["Prozesserhebung und Change-Konzept für die E-Akte: Ist-Aufnahme, "
          "Soll-Prozesse, Begleitung der Beschäftigten.",
          "Beratungshaus: Organisationsprojekte unter Termindruck geführt."],
    "5": ["Händlerbetreuung und Kundenmanagement aus der Wirtschaft — "
          "Serviceorientierung ist eingeübt."],
    "6": ["Forschungsnahe Projekte begleitet, Mittelverwendung und "
          "Berichtspflichten sind vertraut."],
}


# ----------------------------------------------------------------------------------
# AUFNAHME
# ----------------------------------------------------------------------------------

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def fenster_aufnehmen(hwnd):
    """Fotografiert das Fenster vom Bildschirm.

    PrintWindow wäre der elegantere Weg — es nimmt auch verdeckte Fenster auf.
    Mit Tk liefert es aber ein **vollständig schwarzes Bild**: Tk zeichnet
    nicht auf den übergebenen Gerätekontext. Deshalb der Umweg über den
    Bildschirm; das Fenster wird dafür nach vorn geholt.
    """
    from PIL import ImageGrab

    rahmen = wintypes.RECT()
    # GetWindowRect liefert auch die unsichtbare Schattenzone mit -- im Bild
    # sieht man dann rundherum einen Streifen vom Hintergrund. Die echten
    # Fenstergrenzen kennt nur der Fenstermanager (DWM).
    #   9 = DWMWA_EXTENDED_FRAME_BOUNDS
    ergebnis = ctypes.windll.dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd), ctypes.c_uint(9), ctypes.byref(rahmen),
        ctypes.sizeof(rahmen))
    if ergebnis != 0:
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rahmen))
    # Zwei Pixel abschneiden: die Rahmenlinie und was an den runden Ecken
    # von Windows 11 durchscheint.
    rand = 2
    return ImageGrab.grab(
        bbox=(rahmen.left + rand, rahmen.top + rand,
              rahmen.right - rand, rahmen.bottom - rand),
        all_screens=True)


def bild_pruefen(bild, name):
    """Schlägt Alarm bei einfarbigen Bildern.

    Der erste Anlauf lieferte fünf schwarze PNG — ohne diese Prüfung wären
    sie ins Repo gewandert.
    """
    klein = bild.convert("RGB").resize((60, 40))
    farben = set(klein.getdata())
    if len(farben) < 12:
        raise RuntimeError(
            f"{name}: Das Bild hat nur {len(farben)} Farbtöne — da ist nichts "
            f"drauf. Aufnahme abgebrochen.")
    return len(farben)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ordner = tempfile.mkdtemp(prefix="radar_bilder_")
    print(f"Wegwerf-Ordner: {ordner}")

    # --- Alles auf den Temp-Ordner umbiegen, BEVOR etwas geladen wird -------
    import datenbank as db
    import archiv
    import konfiguration as kfg

    db.DB_PFAD = os.path.join(ordner, "demo.db")
    db.PDF_ORDNER = os.path.join(ordner, "steckbriefe")
    archiv.ARCHIV_ORDNER = os.path.join(ordner, "archiv")
    kfg.PROFIL_DATEI = os.path.join(ordner, "profil.json")
    kfg.FELDER_DATEI = os.path.join(ordner, "berufsfelder.json")
    kfg.GEWICHTE_DATEI = os.path.join(ordner, "gewichtung.json")

    with open(kfg.PROFIL_DATEI, "w", encoding="utf-8") as datei:
        json.dump(DEMO_PROFIL, datei, ensure_ascii=False, indent=2)
    with open(kfg.FELDER_DATEI, "w", encoding="utf-8") as datei:
        json.dump({nr: {"kompetenzen": k} for nr, k in DEMO_KOMPETENZEN.items()},
                  datei, ensure_ascii=False, indent=2)

    import einordnung as eo
    eo.neu_laden()

    # Gegenprobe: Es darf nichts Echtes hereinrutschen.
    geladen = kfg.profil_laden()
    assert geladen["name"] == DEMO_PROFIL["name"], \
        f"Falsches Profil geladen: {geladen['name']!r} — Aufnahme abgebrochen."
    assert not os.path.exists(os.path.join(BASIS, "demo.db"))

    db.einrichten()
    for titel, ag, sektor, ort, region, felder, punkte, frist, _, _ in STELLEN:
        db.speichern(dict(
            url=f"https://beispiel.invalid/{abs(hash(titel)) % 100000}",
            titel=titel, arbeitgeber=ag, quelle="Beispiel", sektor=sektor,
            region=region, ort=ort, felder=felder, feld_haupt=felder[0],
            punkte=punkte, frist=frist,
            volltext="Beispieltext der Ausschreibung. " * 40))
    for nummer, eintrag in enumerate(STELLEN, start=1):
        db.status_setzen([nummer], eintrag[8])
        if eintrag[9]:
            db.favorit_setzen([nummer], True)
    for nummer, text in NOTIZEN.items():
        db.notiz_setzen(nummer, text)
    db.briefing_merken(2, BRIEFING, "qwen3.5:9b")

    # --- Fenster bauen -----------------------------------------------------
    import tkinter as tk
    from stellenradar import App

    wurzel = tk.Tk()
    app = App(wurzel)

    # Neutrale Flaeche hinter das Fenster legen. Windows 11 rundet die Ecken,
    # dort scheint sonst der Schreibtisch durch -- auf jedem Rechner ein
    # anderer. So sehen die Bilder ueberall gleich aus.
    hintergrund = tk.Toplevel(wurzel)
    hintergrund.overrideredirect(True)
    hintergrund.geometry(
        f"{wurzel.winfo_screenwidth()}x{wurzel.winfo_screenheight()}+0+0")
    hintergrund.configure(bg="#DDE3EE")
    hintergrund.attributes("-topmost", True)
    hintergrund.update()

    # Auf den Bildschirm passend, aber nicht kleiner als noetig
    breite = min(1480, wurzel.winfo_screenwidth() - 60)
    hoehe = min(940, wurzel.winfo_screenheight() - 90)
    wurzel.geometry(f"{breite}x{hoehe}+20+20")
    wurzel.update()

    os.makedirs(BILDER, exist_ok=True)
    hwnd = int(wurzel.wm_frame(), 16)

    aufnahmen = [
        ("01-dashboard", "dashboard", "Dashboard mit Fristen-Ampel"),
        ("02-liste-neu", db.NEU, "Trefferliste mit Passungs-Punkten"),
        ("03-favoriten", "favoriten", "Favorit mit KI-Briefing"),
        ("04-berufsfelder", "berufsfelder", "Berufsfelder und Kompetenzen"),
        ("05-gewichtung", "gewichtung", "Gewichtung der Punkte"),
    ]

    for name, schluessel, beschreibung in aufnahmen:
        if schluessel == "favoriten":
            # Die Ansicht waehlt in laden() den ersten Favoriten. Wir wollen
            # den mit dem Briefing -- also vorher setzen, nicht nachher.
            app.ansichten["favoriten"].gewaehlt = 2
        app.zeigen(schluessel)
        # Nach vorn holen und wirklich fertig zeichnen lassen, sonst
        # fotografiert man den halb aufgebauten Zustand.
        wurzel.attributes("-topmost", True)
        wurzel.lift(hintergrund)
        wurzel.update_idletasks()
        wurzel.update()
        time.sleep(0.6)
        for _ in range(4):
            wurzel.update_idletasks()
            wurzel.update()
        bild = fenster_aufnehmen(hwnd)
        toene = bild_pruefen(bild, name)
        ziel = os.path.join(BILDER, f"{name}.png")
        bild.save(ziel, optimize=True)
        kb = os.path.getsize(ziel) / 1024
        print(f"  {bild.size[0]}x{bild.size[1]}  {toene:3} Farbtöne  "
              f"{kb:6.0f} KB  {name}.png   ({beschreibung})")

    hintergrund.destroy()
    wurzel.destroy()
    print("\nFertig. Echte Daten und das eigene Profil blieben unberührt.")


if __name__ == "__main__":
    main()
