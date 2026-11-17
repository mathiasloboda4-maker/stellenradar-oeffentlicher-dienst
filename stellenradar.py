# -*- coding: utf-8 -*-
"""Stellenradar — Hauptfenster.

Aufbau: dunkle Seitenleiste links, heller Inhaltsbereich rechts, Kopfzeile mit
den Aktionen. Acht Ansichten:

  Dashboard    Fristen-Ampel, Kennzahlen, was als Nächstes ansteht
  Neu          frisch gefundene Stellen — hier wird sortiert
  Vorgemerkt   die Merkliste, Grundlage für das Dossier
  Beworben     laufende Bewerbungen
  Verworfen    Papierkorb, jederzeit zurückholbar
  Berufsfelder Felder, Stichworte und Kompetenzen ansehen und ändern
  Gewichtung   wie viele Punkte wofür — Nähe oder Entgelt, je nach Lage
  Archiv       die gesicherten Ausschreibungsseiten

Selbsttests:  python stellenradar.py --selftest
              python stellenradar.py --guitest
"""

import json
import os
import subprocess
import sys
import threading
import queue
import webbrowser
from datetime import date, datetime

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

BASIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASIS)

import archiv                                # noqa: E402
import datenbank as db                       # noqa: E402
import einordnung as eo                      # noqa: E402
import konfiguration as kfg                  # noqa: E402
import steckbrief as sb                      # noqa: E402
from oberflaeche import (FLAECHE, KARTE, LINIE, SEITE, SEITE_HELL, SEITE_AKTIV,
                         TEXT, TEXT_LEISE, TEXT_HELL, INDIGO, VIOLETT, BLAU,
                         TUERKIS, MINT, GELB, KORALLE, ROT, SCHRIFT, S_KLEIN,
                         S_NORMAL, S_MITTEL, S_FETT, S_TITEL, S_GROSS, S_ZAHL,
                         Karte, balken, eingabe, knopf, marke, rollbereich,
                         symbolplaettchen, tabellenstil, textfeld, trenner,
                         ueberschrift, zahlfeld, zart)   # noqa: E402

# Fristen-Ampel: Schlüssel, Beschriftung, Farbe
AMPEL = [
    ("abgelaufen", "Frist abgelaufen", ROT),
    ("heute_morgen", "Heute oder morgen", KORALLE),
    ("woche", "Diese Woche", GELB),
    ("zwei_wochen", "In zwei Wochen", TUERKIS),
    ("spaeter", "Später", MINT),
    ("ohne", "Ohne Fristangabe", TEXT_LEISE),
]
AMPEL_FARBE = {fach: farbe for fach, _, farbe in AMPEL}

SORTIERUNGEN = {
    "Beste Passung zuerst": "punkte",
    "Frist zuerst": "frist",
    "Zuletzt gefunden": "neu",
    "Nach Arbeitgeber": "arbeitgeber",
}

FEHLERPROTOKOLL = os.path.join(BASIS, "fehler.log")
LAUFPROTOKOLL = os.path.join(BASIS, "lauf.log")


# ----------------------------------------------------------------------------------
# HILFEN
# ----------------------------------------------------------------------------------

def dpi_beachten():
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def datei_oeffnen(pfad):
    try:
        os.startfile(pfad)
    except Exception:
        subprocess.Popen(["cmd", "/c", "start", "", pfad], shell=False)


def datum_de(iso):
    if not iso:
        return ""
    try:
        return date.fromisoformat(iso).strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return str(iso)


def frist_text(frist):
    """Lesbare Frist plus das Fach der Ampel."""
    tage = db.tage_bis_frist(frist)
    if tage is None:
        return ("—", "ohne")
    datum = datum_de(frist)
    if tage < 0:
        return (f"{datum} · abgelaufen", "abgelaufen")
    if tage == 0:
        return (f"{datum} · HEUTE", "heute_morgen")
    if tage == 1:
        return (f"{datum} · morgen", "heute_morgen")
    if tage <= 7:
        return (f"{datum} · in {tage} Tagen", "woche")
    if tage <= 14:
        return (f"{datum} · in {tage} Tagen", "zwei_wochen")
    return (f"{datum} · in {tage} Tagen", "spaeter")


def feld_nummern(zeile):
    try:
        nummern = json.loads(zeile["felder"] or "[]")
    except (ValueError, TypeError):
        nummern = []
    if not nummern and zeile["feld_haupt"]:
        nummern = [zeile["feld_haupt"]]
    return nummern


def feld_zeichen(zeile):
    return " ".join(eo.FELD_KURZ.get(n, "") for n in feld_nummern(zeile)[:3])


def spaltenwert(zeile, name, standard=None):
    """Liest eine Spalte, die es in älteren Datenbanken noch nicht gab."""
    try:
        return zeile[name]
    except (KeyError, IndexError):
        return standard


# ----------------------------------------------------------------------------------
# ANSICHT: STELLENLISTE
# ----------------------------------------------------------------------------------

class ListenAnsicht(tk.Frame):

    SPALTEN = [
        ("favorit", "★", 34, "center"),
        ("punkte", "Punkte", 64, "center"),
        ("frist", "Frist", 168, "w"),
        ("titel", "Stelle", 380, "w"),
        ("arbeitgeber", "Arbeitgeber", 210, "w"),
        ("ort", "Ort", 120, "w"),
        ("entgelt", "Entgelt", 68, "center"),
        ("feld", "Feld", 70, "center"),
        ("archiv", "PDF", 46, "center"),
    ]

    TITEL = {
        db.NEU: ("Neue Stellen", "Jede Stelle einmal ansehen: vormerken oder verwerfen. "
                                 "Verworfene kommen nie wieder."),
        db.VORGEMERKT: ("Merkliste", "Diese Stellen kommen ins Dossier."),
        db.BEWORBEN: ("Beworben", "Laufende Bewerbungen."),
        db.VERWORFEN: ("Verworfen", "Nicht passend. Lässt sich jederzeit zurückholen."),
    }

    # Im Reiter „Beworben" zaehlt der Verlauf, nicht die Passung.
    SPALTEN_BEWORBEN = [
        ("favorit", "★", 34, "center"),
        ("beworben_am", "Beworben am", 110, "center"),
        ("rueckmeldung", "Rückmeldung", 160, "w"),
        ("wiedervorlage", "Wiedervorlage", 130, "center"),
        ("titel", "Stelle", 340, "w"),
        ("arbeitgeber", "Arbeitgeber", 200, "w"),
        ("ort", "Ort", 110, "w"),
    ]

    def __init__(self, eltern, app, status):
        super().__init__(eltern, bg=FLAECHE)
        self.app = app
        self.status = status
        self.zeilen = {}
        if status == db.BEWORBEN:
            self.SPALTEN = self.SPALTEN_BEWORBEN
        self._bauen()

    def _bauen(self):
        titel, unterzeile = self.TITEL[self.status]
        ueberschrift(self, titel, unterzeile).pack(fill="x", padx=24, pady=(16, 10))

        # Filterkarte
        filterkarte = Karte(self, polster=12, radius=12)
        filterkarte.pack(fill="x", padx=24, pady=(0, 12))
        reihe = filterkarte.innen

        tk.Label(reihe, text="🔎", bg=KARTE, fg=TEXT_LEISE,
                 font=(SCHRIFT, 11)).pack(side="left", padx=(2, 6))
        rahmen, self.suchfeld = eingabe(reihe, breite=22)
        rahmen.pack(side="left", padx=(0, 16))
        self.suchfeld.bind("<KeyRelease>", lambda e: self.laden())

        self.feld_wahl = self._auswahl(
            reihe, "Berufsfeld",
            ["alle"] + [f"{eo.FELD_KURZ[n]} {eo.FELDER[n]}" for n in sorted(eo.FELDER)],
            breite=30)
        self.sektor_wahl = self._auswahl(
            reihe, "Bereich", ["alle"] + list(eo.SEKTOREN.values()), breite=24)
        self.sortier_wahl = self._auswahl(
            reihe, "Sortierung", list(SORTIERUNGEN), breite=20,
            vorgabe=1 if self.status == db.VORGEMERKT else 0)

        self.anzahl = tk.Label(reihe, text="", bg=KARTE, fg=TEXT_LEISE, font=S_FETT)
        self.anzahl.pack(side="right", padx=4)

        # Knopfleiste unten — vor der Tabelle gepackt, damit sie unten bleibt
        leiste = tk.Frame(self, bg=FLAECHE)
        leiste.pack(side="bottom", fill="x", padx=24, pady=(0, 16))
        self._knoepfe(leiste)

        # Vorschau
        vorschaukarte = Karte(self, polster=14, radius=12)
        vorschaukarte.pack(side="bottom", fill="x", padx=24, pady=(0, 10))
        kopf = tk.Frame(vorschaukarte.innen, bg=KARTE)
        kopf.pack(fill="x")
        tk.Label(kopf, text="Ausschreibung", bg=KARTE, fg=TEXT, font=S_TITEL,
                 anchor="w").pack(side="left")
        self.vorschau_kopf = tk.Label(kopf, text="", bg=KARTE, fg=TEXT_LEISE,
                                      font=S_KLEIN, anchor="e")
        self.vorschau_kopf.pack(side="right")
        feldrahmen, self.vorschau = textfeld(vorschaukarte.innen, hoehe=5)
        feldrahmen.pack(fill="x", pady=(8, 0))
        self.vorschau.configure(state="disabled")

        # Tabelle
        tabellenkarte = Karte(self, polster=10, radius=12)
        tabellenkarte.pack(fill="both", expand=True, padx=24, pady=(0, 10))
        spalten = [s[0] for s in self.SPALTEN]
        self.tabelle = ttk.Treeview(tabellenkarte.innen, columns=spalten,
                                    show="headings", selectmode="extended",
                                    style="Radar.Treeview")
        for schluessel, beschriftung, breite, ausrichtung in self.SPALTEN:
            self.tabelle.heading(schluessel, text=beschriftung)
            self.tabelle.column(schluessel, width=breite, anchor=ausrichtung,
                                stretch=(schluessel in ("titel", "arbeitgeber")))
        senkrecht = ttk.Scrollbar(tabellenkarte.innen, orient="vertical",
                                  command=self.tabelle.yview,
                                  style="Radar.Vertical.TScrollbar")
        self.tabelle.configure(yscrollcommand=senkrecht.set)
        senkrecht.pack(side="right", fill="y")
        self.tabelle.pack(fill="both", expand=True)

        for fach, _, farbe in AMPEL:
            self.tabelle.tag_configure(fach, foreground=farbe)
        self.tabelle.tag_configure("wechsel", background="#FAFBFE")

        self.tabelle.bind("<<TreeviewSelect>>", lambda e: self._vorschau_zeigen())
        self.tabelle.bind("<Double-1>", lambda e: self.im_browser())
        self.tabelle.bind("<Delete>", lambda e: self.status_setzen(db.VERWORFEN))
        self.tabelle.bind("<Control-a>", self._alle_markieren)
        self.tabelle.bind("<Button-3>", self._kontextmenue)

    def _auswahl(self, eltern, beschriftung, werte, breite=24, vorgabe=0):
        tk.Label(eltern, text=beschriftung, bg=KARTE, fg=TEXT_LEISE,
                 font=S_KLEIN).pack(side="left", padx=(0, 5))
        feld = ttk.Combobox(eltern, width=breite, state="readonly", font=S_NORMAL,
                            values=werte)
        feld.current(vorgabe)
        feld.pack(side="left", padx=(0, 16))
        feld.bind("<<ComboboxSelected>>", lambda e: self.laden())
        return feld

    def _knoepfe(self, leiste):
        if self.status != db.VORGEMERKT:
            knopf(leiste, "⭐  Vormerken",
                  lambda: self.status_setzen(db.VORGEMERKT), MINT,
                  hintergrund=FLAECHE).pack(side="left", padx=(0, 8))
        if self.status != db.BEWORBEN:
            knopf(leiste, "✉  Beworben", lambda: self.status_setzen(db.BEWORBEN),
                  INDIGO, hintergrund=FLAECHE).pack(side="left", padx=(0, 8))
        if self.status != db.VERWORFEN:
            knopf(leiste, "🗑  Verwerfen", lambda: self.status_setzen(db.VERWORFEN),
                  ROT, hell=True, hintergrund=FLAECHE).pack(side="left", padx=(0, 8))
        else:
            knopf(leiste, "↩  Zurückholen", lambda: self.status_setzen(db.NEU),
                  MINT, hintergrund=FLAECHE).pack(side="left", padx=(0, 8))

        knopf(leiste, "★  Favorit", self.favorit_umschalten, GELB, hell=True,
              hintergrund=FLAECHE).pack(side="left", padx=(0, 8))

        if self.status in (db.BEWORBEN, db.VORGEMERKT):
            knopf(leiste, "📅  Verlauf", self.verlauf_bearbeiten, VIOLETT,
                  hintergrund=FLAECHE).pack(side="left", padx=(0, 8))

        for text, befehl in (("🌐  Im Browser", self.im_browser),
                             ("📄  Steckbrief", self.steckbrief),
                             ("📑  Seite als PDF", self.archivieren),
                             ("📝  Notiz", self.notiz)):
            knopf(leiste, text, befehl, TEXT_LEISE, hell=True,
                  hintergrund=FLAECHE).pack(side="left", padx=(0, 6))

    # -- Daten ---------------------------------------------------------------
    def laden(self):
        suche = self.suchfeld.get().strip() or None

        feld = None
        gewaehlt = self.feld_wahl.get()
        if gewaehlt != "alle":
            for nummer, name in eo.FELDER.items():
                if name in gewaehlt:
                    feld = nummer
                    break

        sektor = None
        gewaehlt = self.sektor_wahl.get()
        if gewaehlt != "alle":
            for schluessel, name in eo.SEKTOREN.items():
                if name == gewaehlt:
                    sektor = schluessel
                    break

        zeilen = db.holen(status=self.status, feld=feld, sektor=sektor, suche=suche,
                          sortierung=SORTIERUNGEN.get(self.sortier_wahl.get(), "punkte"))

        self.tabelle.delete(*self.tabelle.get_children())
        self.zeilen = {}
        for nummer, zeile in enumerate(zeilen):
            text, fach = frist_text(zeile["frist"])
            hat_pdf = bool(spaltenwert(zeile, "archiv_pdf"))
            marken = [fach] + (["wechsel"] if nummer % 2 else [])
            self.zeilen[str(zeile["id"])] = zeile
            stern = "★" if spaltenwert(zeile, "favorit") else ""
            if self.status == db.BEWORBEN:
                werte = (stern, datum_de(spaltenwert(zeile, "beworben_am")) or "—",
                         spaltenwert(zeile, "rueckmeldung") or "—",
                         self._wiedervorlage_text(zeile), zeile["titel"],
                         zeile["arbeitgeber"] or "", zeile["ort"] or "")
            else:
                werte = (stern, zeile["punkte"], text, zeile["titel"],
                         zeile["arbeitgeber"] or "", zeile["ort"] or "",
                         zeile["entgelt"] or "—", feld_zeichen(zeile),
                         "✓" if hat_pdf else "·")
            self.tabelle.insert("", "end", iid=str(zeile["id"]),
                                tags=tuple(marken), values=werte)
        self.anzahl.config(text=f"{len(zeilen)} Stellen")
        self._vorschau_leeren()

    def _markierte(self):
        return list(self.tabelle.selection())

    def _alle_markieren(self, ereignis=None):
        self.tabelle.selection_set(self.tabelle.get_children())
        return "break"

    def _vorschau_leeren(self):
        self.vorschau_kopf.config(text="")
        self.vorschau.config(state="normal")
        self.vorschau.delete("1.0", "end")
        self.vorschau.insert("1.0", "Eine Zeile anklicken, um die Ausschreibung "
                                    "hier zu lesen.")
        self.vorschau.config(state="disabled")

    def _vorschau_zeigen(self):
        markiert = self._markierte()
        if len(markiert) != 1:
            self._vorschau_leeren()
            return
        zeile = self.zeilen.get(markiert[0])
        if not zeile:
            return

        kopfzeile = []
        if zeile["punkte_gruende"]:
            kopfzeile.append(f"Punkte {zeile['punkte']} — {zeile['punkte_gruende']}")
        angaben = " · ".join(filter(None, [
            zeile["eintritt"] and f"Eintritt: {zeile['eintritt']}",
            zeile["umfang"], zeile["befristung"], zeile["kontakt"], zeile["telefon"],
            zeile["email"],
            zeile["entfernung_km"] is not None and f"{zeile['entfernung_km']} km",
            zeile["quelle"] and f"Quelle: {zeile['quelle']}",
        ]))
        if angaben:
            kopfzeile.append(angaben)
        if zeile["notiz"]:
            kopfzeile.append(f"Notiz: {zeile['notiz']}")

        text = "\n".join(kopfzeile) + "\n\n" + (
            zeile["volltext"] or "(Kein Ausschreibungstext gespeichert — über "
                                 "„🌐 Im Browser\" nachlesen.)")
        self.vorschau.config(state="normal")
        self.vorschau.delete("1.0", "end")
        self.vorschau.insert("1.0", text)
        self.vorschau.config(state="disabled")

        archivpfad = spaltenwert(zeile, "archiv_pdf")
        if archivpfad and os.path.exists(archivpfad):
            self.vorschau_kopf.config(text="📑 Seite ist archiviert — "
                                           "Doppelklick auf „Seite als PDF\" öffnet sie")
        else:
            self.vorschau_kopf.config(text="📑 noch nicht archiviert")

    # -- Aktionen ------------------------------------------------------------
    def status_setzen(self, neuer_status):
        markiert = self._markierte()
        if not markiert:
            self.app.melden("Bitte zuerst eine oder mehrere Zeilen anklicken.")
            return
        db.status_setzen(markiert, neuer_status)
        self.app.melden(f"{len(markiert)} Stelle(n) → "
                        f"{db.STATUS_NAMEN[neuer_status]}")
        self.app.alles_neu_laden()

    def favorit_umschalten(self):
        """Stern an oder aus. Favoriten erscheinen in der eigenen Ansicht."""
        markiert = self._markierte()
        if not markiert:
            self.app.melden("Bitte zuerst eine oder mehrere Zeilen anklicken.")
            return
        # Ist mindestens eine noch kein Favorit, werden alle zu Favoriten.
        setzen = any(not spaltenwert(self.zeilen.get(k), "favorit")
                     for k in markiert if self.zeilen.get(k))
        db.favorit_setzen(markiert, setzen)
        self.app.melden(f"{len(markiert)} Stelle(n) "
                        f"{'als Favorit markiert' if setzen else 'aus den Favoriten entfernt'}.")
        self.app.alles_neu_laden()

    def im_browser(self):
        markiert = self._markierte()
        if not markiert:
            self.app.melden("Bitte zuerst eine Zeile anklicken.")
            return
        for kennung in markiert[:6]:
            zeile = self.zeilen.get(kennung)
            if zeile and zeile["url"]:
                webbrowser.open(zeile["url"])
        self.app.melden(f"{min(len(markiert), 6)} Ausschreibung(en) geöffnet.")

    def steckbrief(self):
        markiert = self._markierte()
        if not markiert:
            self.app.melden("Bitte zuerst eine oder mehrere Zeilen anklicken.")
            return
        self.app.steckbriefe_erzeugen(markiert)

    def archivieren(self):
        """Archivierte Seite öffnen — oder nachträglich anlegen."""
        markiert = self._markierte()
        if not markiert:
            self.app.melden("Bitte zuerst eine Zeile anklicken.")
            return
        offen = []
        for kennung in markiert:
            zeile = self.zeilen.get(kennung)
            pfad = spaltenwert(zeile, "archiv_pdf") if zeile else None
            if pfad and os.path.exists(pfad):
                datei_oeffnen(pfad)
            else:
                offen.append(kennung)
        if offen:
            self.app.archivieren_starten(offen)
        elif markiert:
            self.app.melden("Archivierte Seite(n) geöffnet.")

    def _wiedervorlage_text(self, zeile):
        """Wiedervorlage mit Restlaufzeit — Fälliges soll ins Auge springen."""
        wann = spaltenwert(zeile, "wiedervorlage")
        if not wann:
            return "—"
        tage = db.tage_bis_frist(wann)
        if tage is None:
            return str(wann)
        if tage < 0:
            return f"{datum_de(wann)} ‹ fällig"
        if tage == 0:
            return f"{datum_de(wann)} · HEUTE"
        return f"{datum_de(wann)} · in {tage} T."

    def verlauf_bearbeiten(self):
        """Bewerbungsdatum, Rückmeldung und Wiedervorlage festhalten."""
        markiert = self._markierte()
        if len(markiert) != 1:
            self.app.melden("Für den Verlauf bitte genau eine Zeile anklicken.")
            return
        VerlaufDialog(self, self.app, markiert[0])

    def notiz(self):
        markiert = self._markierte()
        if len(markiert) != 1:
            self.app.melden("Für eine Notiz bitte genau eine Zeile anklicken.")
            return
        zeile = self.zeilen.get(markiert[0])
        neu = simpledialog.askstring("Notiz", f"Notiz zu „{zeile['titel'][:58]}“:",
                                     initialvalue=zeile["notiz"] or "", parent=self)
        if neu is not None:
            db.notiz_setzen(markiert[0], neu)
            self.laden()
            self.app.melden("Notiz gespeichert.")

    def _kontextmenue(self, ereignis):
        zeile = self.tabelle.identify_row(ereignis.y)
        if zeile and zeile not in self.tabelle.selection():
            self.tabelle.selection_set(zeile)
        menue = tk.Menu(self, tearoff=0, font=S_NORMAL)
        menue.add_command(label="🌐  Im Browser öffnen", command=self.im_browser)
        menue.add_command(label="📑  Archivierte Seite", command=self.archivieren)
        menue.add_command(label="📄  Steckbrief erzeugen", command=self.steckbrief)
        menue.add_command(label="📝  Notiz …", command=self.notiz)
        menue.add_separator()
        menue.add_command(label="★  Favorit an/aus", command=self.favorit_umschalten)
        menue.add_command(label="⭐  Vormerken",
                          command=lambda: self.status_setzen(db.VORGEMERKT))
        menue.add_command(label="✉  Beworben",
                          command=lambda: self.status_setzen(db.BEWORBEN))
        menue.add_command(label="🗑  Verwerfen",
                          command=lambda: self.status_setzen(db.VERWORFEN))
        menue.add_separator()
        menue.add_command(label="Alle markieren (Strg+A)",
                          command=lambda: self._alle_markieren())
        try:
            menue.tk_popup(ereignis.x_root, ereignis.y_root)
        finally:
            menue.grab_release()


class ErfassenDialog(tk.Toplevel):
    """Eine Stelle von Hand eintragen.

    Nicht alles kommt über die Portale — ein Hinweis aus dem Bekanntenkreis,
    ein Fund auf LinkedIn. Ohne diesen Weg lebt so eine Stelle außerhalb des
    Programms: kein Briefing, keine Seitenkopie, keine Frist im Dashboard.
    """

    def __init__(self, eltern, app):
        super().__init__(eltern)
        self.app = app
        self.title("Stelle von Hand erfassen")
        self.configure(bg=FLAECHE)
        self.geometry("680x560")
        self.transient(eltern)
        self._bauen()
        self.grab_set()

    def _bauen(self):
        karte = Karte(self, polster=18, radius=14)
        karte.pack(fill="both", expand=True, padx=16, pady=16)
        innen = karte.innen

        tk.Label(innen, text="Stelle von Hand erfassen", bg=KARTE, fg=TEXT,
                 font=S_TITEL, anchor="w").pack(fill="x")
        tk.Label(innen,
                 text="Für Ausschreibungen, die der Suchlauf nicht findet — aus "
                      "dem Bekanntenkreis, von LinkedIn oder per Mail. Sie landet "
                      "in derselben Liste und wird von keinem Suchlauf aussortiert.",
                 bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN, anchor="w",
                 justify="left", wraplength=600).pack(fill="x", pady=(2, 14))

        tk.Label(innen, text="Link zur Ausschreibung", bg=KARTE, fg=TEXT_LEISE,
                 font=S_KLEIN, anchor="w").pack(fill="x")
        reihe = tk.Frame(innen, bg=KARTE)
        reihe.pack(fill="x", pady=(2, 4))
        rahmen, self.url = eingabe(reihe, breite=52)
        rahmen.pack(side="left", fill="x", expand=True)
        knopf(reihe, "Einfügen", self._aus_zwischenablage, TEXT_LEISE,
              hell=True).pack(side="left", padx=6)
        self.url.bind("<Return>", lambda e: self._aus_link())

        tk.Label(innen,
                 text="Angaben, die das Programm nicht aus dem Text ziehen kann "
                      "(beides freiwillig):",
                 bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN, anchor="w").pack(
            fill="x", pady=(10, 2))
        reihe2 = tk.Frame(innen, bg=KARTE)
        reihe2.pack(fill="x", pady=(0, 10))
        tk.Label(reihe2, text="Arbeitgeber", bg=KARTE, fg=TEXT_LEISE,
                 font=S_KLEIN).pack(side="left")
        rahmen, self.arbeitgeber = eingabe(reihe2, breite=26)
        rahmen.pack(side="left", padx=(5, 14))
        tk.Label(reihe2, text="Bereich", bg=KARTE, fg=TEXT_LEISE,
                 font=S_KLEIN).pack(side="left")
        self.sektor = ttk.Combobox(reihe2, values=list(eo.SEKTOREN.values()),
                                   state="readonly", width=22, font=S_NORMAL)
        self.sektor.pack(side="left", padx=5)
        self.sektor.set(eo.SEKTOREN["oed_bb"])

        knopf(innen, "🌐  Von der Seite holen", self._aus_link, INDIGO,
              breit=True).pack(anchor="w")

        tk.Frame(innen, bg=LINIE, height=1).pack(fill="x", pady=14)

        tk.Label(innen, text="Oder: Text von Hand einfügen", bg=KARTE, fg=TEXT,
                 font=S_FETT, anchor="w").pack(fill="x")
        tk.Label(innen,
                 text="Wenn die Seite sich nicht abrufen lässt. Ausschreibung im "
                      "Browser öffnen, Strg+A, Strg+C, hier Strg+V. Die erste Zeile "
                      "gilt als Stellenbezeichnung.",
                 bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN, anchor="w",
                 justify="left", wraplength=600).pack(fill="x", pady=(2, 6))
        rahmen, self.text = textfeld(innen, hoehe=8)
        rahmen.pack(fill="both", expand=True)

        leiste = tk.Frame(innen, bg=KARTE)
        leiste.pack(fill="x", pady=(12, 0))
        knopf(leiste, "Schließen", self.destroy, TEXT_LEISE, hell=True).pack(
            side="right", padx=(8, 0))
        knopf(leiste, "📝  Text übernehmen", self._aus_text, MINT).pack(side="right")

    def _aus_zwischenablage(self):
        try:
            inhalt = self.clipboard_get()
        except Exception:
            return
        self.url.delete(0, "end")
        self.url.insert(0, inhalt.strip())

    def _sektor_schluessel(self):
        for schluessel, name in eo.SEKTOREN.items():
            if name == self.sektor.get():
                return schluessel
        return "privat"

    def _aus_link(self):
        import erfassen
        adresse = self.url.get().strip()
        if not adresse:
            self.app.melden("Bitte zuerst den Link einfügen.")
            return
        self.app.melden("Rufe die Seite ab …")
        self.update_idletasks()
        try:
            kennung, ist_neu, hinweis = erfassen.aus_link(
                adresse, arbeitgeber=self.arbeitgeber.get().strip() or None,
                sektor=self._sektor_schluessel())
        except Exception as fehler:
            messagebox.showwarning("Erfassen", str(fehler), parent=self)
            self.app.melden("Die Seite konnte nicht gelesen werden.")
            return
        self._fertig(kennung, ist_neu, hinweis)

    def _aus_text(self):
        import erfassen
        roh = self.text.get("1.0", "end").strip()
        if not roh:
            self.app.melden("Bitte zuerst den Ausschreibungstext einfügen.")
            return
        zeilen = [z.strip() for z in roh.splitlines() if z.strip()]
        titel = zeilen[0] if zeilen else ""
        try:
            kennung, ist_neu, hinweis = erfassen.aus_text(
                titel, roh, url=self.url.get().strip() or None,
                arbeitgeber=self.arbeitgeber.get().strip() or None,
                sektor=self._sektor_schluessel())
        except Exception as fehler:
            messagebox.showwarning("Erfassen", str(fehler), parent=self)
            return
        self._fertig(kennung, ist_neu, hinweis)

    def _fertig(self, kennung, ist_neu, hinweis):
        zeile = db.eine(kennung)
        meldung = (f"{'Angelegt' if ist_neu else 'Aktualisiert'}: "
                   f"{zeile['titel'][:60]}")
        if hinweis:
            meldung += f"  (Filter hätte sie aussortiert: {hinweis})"
        self.app.melden(meldung)
        self.app.alles_neu_laden()
        self.destroy()
        if messagebox.askyesno(
                "Stelle erfasst",
                f"{zeile['titel'][:70]}\n\n"
                f"Arbeitgeber: {zeile['arbeitgeber'] or 'unbekannt'}\n"
                f"Frist: {datum_de(zeile['frist']) or 'nicht angegeben'}\n"
                f"Punkte: {zeile['punkte']}\n\n"
                f"Jetzt die Seite als PDF sichern?"):
            self.app.archivieren_starten([kennung])


class VerlaufDialog(tk.Toplevel):
    """Kleiner Dialog für den Stand einer Bewerbung."""

    RUECKMELDUNGEN = ["", "Eingangsbestätigung", "Einladung zum Gespräch",
                      "Gespräch geführt", "Zweitgespräch", "Zusage", "Absage",
                      "keine Reaktion"]

    def __init__(self, eltern, app, kennung):
        super().__init__(eltern)
        self.app = app
        self.kennung = kennung
        self.zeile = db.eine(kennung)
        self.title("Verlauf der Bewerbung")
        self.configure(bg=FLAECHE)
        self.geometry("560x430")
        self.transient(eltern.winfo_toplevel())
        self._bauen()
        self.grab_set()

    def _bauen(self):
        karte = Karte(self, polster=18, radius=14)
        karte.pack(fill="both", expand=True, padx=16, pady=16)
        innen = karte.innen

        tk.Label(innen, text=self.zeile["titel"][:70], bg=KARTE, fg=TEXT,
                 font=S_TITEL, anchor="w", wraplength=480,
                 justify="left").pack(fill="x")
        tk.Label(innen, text=self.zeile["arbeitgeber"] or "", bg=KARTE,
                 fg=TEXT_LEISE, font=S_NORMAL, anchor="w").pack(fill="x", pady=(0, 14))

        tk.Label(innen, text="Beworben am  (TT.MM.JJJJ)", bg=KARTE, fg=TEXT_LEISE,
                 font=S_KLEIN, anchor="w").pack(fill="x")
        zeile1 = tk.Frame(innen, bg=KARTE)
        zeile1.pack(fill="x", pady=(2, 12))
        rahmen, self.beworben = eingabe(zeile1, breite=14)
        rahmen.pack(side="left")
        self.beworben.insert(0, datum_de(spaltenwert(self.zeile, "beworben_am")))
        knopf(zeile1, "heute", lambda: self._setzen(self.beworben, 0), MINT,
              hell=True).pack(side="left", padx=8)

        tk.Label(innen, text="Rückmeldung", bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN,
                 anchor="w").pack(fill="x")
        self.rueckmeldung = ttk.Combobox(innen, values=self.RUECKMELDUNGEN,
                                         font=S_NORMAL, width=34)
        self.rueckmeldung.pack(fill="x", pady=(2, 12), ipady=2)
        self.rueckmeldung.set(spaltenwert(self.zeile, "rueckmeldung") or "")

        tk.Label(innen, text="Wiedervorlage — erinnere mich an diesem Tag",
                 bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN, anchor="w").pack(fill="x")
        zeile2 = tk.Frame(innen, bg=KARTE)
        zeile2.pack(fill="x", pady=(2, 6))
        rahmen, self.wiedervorlage = eingabe(zeile2, breite=14)
        rahmen.pack(side="left")
        self.wiedervorlage.insert(0, datum_de(spaltenwert(self.zeile, "wiedervorlage")))
        for text, tage in (("in 1 Woche", 7), ("in 2 Wochen", 14), ("in 4 Wochen", 28)):
            knopf(zeile2, text, lambda d=tage: self._setzen(self.wiedervorlage, d),
                  BLAU, hell=True).pack(side="left", padx=4)

        tk.Label(innen, text="Fällige Wiedervorlagen stehen im Dashboard ganz oben.",
                 bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN, anchor="w").pack(
            fill="x", pady=(0, 10))

        leiste = tk.Frame(innen, bg=KARTE)
        leiste.pack(fill="x", side="bottom")
        knopf(leiste, "Abbrechen", self.destroy, TEXT_LEISE, hell=True).pack(
            side="right", padx=(8, 0))
        knopf(leiste, "Speichern", self._speichern, MINT).pack(side="right")

    def _setzen(self, feld, tage):
        from datetime import timedelta
        feld.delete(0, "end")
        feld.insert(0, (date.today() + timedelta(days=tage)).strftime("%d.%m.%Y"))

    def _lesen(self, feld):
        """Nimmt TT.MM.JJJJ und gibt ISO zurück. Leer bleibt leer."""
        roh = feld.get().strip()
        if not roh:
            return ""
        for muster in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
            try:
                return datetime.strptime(roh, muster).date().isoformat()
            except ValueError:
                continue
        raise ValueError(f"'{roh}' ist kein Datum. "
                         f"Bitte als TT.MM.JJJJ eintragen.")

    def _speichern(self):
        try:
            beworben = self._lesen(self.beworben)
            wieder = self._lesen(self.wiedervorlage)
        except ValueError as fehler:
            messagebox.showwarning("Datum", str(fehler), parent=self)
            return
        db.verlauf_setzen(self.kennung, beworben_am=beworben,
                          rueckmeldung=self.rueckmeldung.get().strip(),
                          wiedervorlage=wieder)
        # Wer ein Bewerbungsdatum einträgt, hat sich beworben.
        if beworben and self.zeile["status"] != db.BEWORBEN:
            db.status_setzen([self.kennung], db.BEWORBEN)
        self.app.melden("Verlauf gespeichert.")
        self.app.alles_neu_laden()
        self.destroy()


# ----------------------------------------------------------------------------------
# ANSICHT: DASHBOARD
# ----------------------------------------------------------------------------------

class DashboardAnsicht(tk.Frame):

    def __init__(self, eltern, app):
        super().__init__(eltern, bg=FLAECHE)
        self.app = app
        self.aussen, self.inhalt = rollbereich(self)
        self.aussen.pack(fill="both", expand=True)

    def laden(self):
        for kind in self.inhalt.winfo_children():
            kind.destroy()
        zahlen = db.kennzahlen()

        ueberschrift(self.inhalt, "Dashboard",
                     f"Stand {datetime.now().strftime('%d.%m.%Y, %H:%M')} · "
                     f"{zahlen['gesamt']} Stellen insgesamt").pack(
            fill="x", padx=24, pady=(20, 14))

        self._handlungsbedarf()
        self._kennzahlen(zahlen)
        self._ampel(zahlen)
        self._naechste(zahlen)
        self._verteilung(zahlen)
        self._letzter_lauf(zahlen)

    def _handlungsbedarf(self):
        """Ganz oben: Was jetzt zu tun ist — fällige Wiedervorlagen und
        abgelaufene Stellen, die noch herumliegen. Beides geht sonst unter."""
        faellig = db.wiedervorlagen()
        abgelaufen = db.abgelaufene(db.NEU)
        if not faellig and not abgelaufen:
            return

        karte = Karte(self.inhalt, polster=16, radius=14, fuellung="#FFF8E8",
                      rand="#F0D9A8")
        karte.pack(fill="x", padx=24, pady=(0, 10))
        innen = karte.innen
        kopf = tk.Frame(innen, bg="#FFF8E8")
        kopf.pack(fill="x")
        tk.Label(kopf, text="⏰  Das wartet auf dich", bg="#FFF8E8", fg="#8A5A00",
                 font=S_TITEL, anchor="w").pack(side="left")

        for zeile in faellig[:6]:
            reihe = tk.Frame(innen, bg="#FFF8E8", cursor="hand2")
            reihe.pack(fill="x", pady=(6, 0))
            tage = db.tage_bis_frist(spaltenwert(zeile, "wiedervorlage"))
            text = ("heute" if tage == 0
                    else f"seit {abs(tage)} Tagen" if tage and tage < 0 else "")
            tk.Label(reihe, text=f"Wiedervorlage {text}", bg="#FFF8E8", fg=KORALLE,
                     font=S_FETT, width=24, anchor="w").pack(side="left")
            tk.Label(reihe, text=zeile["titel"][:60], bg="#FFF8E8", fg=TEXT,
                     font=S_NORMAL, anchor="w").pack(side="left")
            rueck = spaltenwert(zeile, "rueckmeldung")
            tk.Label(reihe, text=f"  ({(zeile['arbeitgeber'] or '')[:30]}"
                                 f"{', ' + rueck if rueck else ''})",
                     bg="#FFF8E8", fg=TEXT_LEISE, font=S_KLEIN,
                     anchor="w").pack(side="left")
            for widget in (reihe,) + tuple(reihe.winfo_children()):
                widget.bind("<Button-1>",
                            lambda e: self.app.zeigen(db.BEWORBEN))

        if abgelaufen:
            reihe = tk.Frame(innen, bg="#FFF8E8")
            reihe.pack(fill="x", pady=(10, 0))
            tk.Label(reihe, text=f"{len(abgelaufen)} Stellen sind abgelaufen und "
                                 f"stehen noch auf „neu“.",
                     bg="#FFF8E8", fg="#8A5A00", font=S_NORMAL,
                     anchor="w").pack(side="left")
            knopf(reihe, "Aufräumen", self.app.abgelaufene_aufraeumen, GELB,
                  hell=True, hintergrund="#FFF8E8").pack(side="left", padx=10)

    def _kennzahlen(self, zahlen):
        reihe = tk.Frame(self.inhalt, bg=FLAECHE)
        reihe.pack(fill="x", padx=20, pady=(0, 6))
        kacheln = [
            ("🆕", "Neu", zahlen["status"].get(db.NEU, 0), INDIGO, db.NEU),
            ("⭐", "Vorgemerkt", zahlen["status"].get(db.VORGEMERKT, 0), MINT,
             db.VORGEMERKT),
            ("✉", "Beworben", zahlen["status"].get(db.BEWORBEN, 0), VIOLETT,
             db.BEWORBEN),
            ("🗑", "Verworfen", zahlen["status"].get(db.VERWORFEN, 0), TEXT_LEISE,
             db.VERWORFEN),
        ]
        for zeichen, name, anzahl, farbe, ziel in kacheln:
            karte = Karte(reihe, polster=16, radius=14)
            karte.pack(side="left", fill="both", expand=True, padx=4)
            innen = karte.innen
            kopf = tk.Frame(innen, bg=KARTE)
            kopf.pack(fill="x")
            symbolplaettchen(kopf, zeichen, farbe, 34).pack(side="left")
            tk.Label(kopf, text=str(anzahl), bg=KARTE, fg=TEXT,
                     font=S_ZAHL).pack(side="right")
            tk.Label(innen, text=name, bg=KARTE, fg=TEXT_LEISE, font=S_NORMAL,
                     anchor="w").pack(fill="x", pady=(8, 0))
            for widget in (karte, innen, kopf):
                widget.bind("<Button-1>", lambda e, z=ziel: self.app.zeigen(z))
                widget.configure(cursor="hand2")

    def _ampel(self, zahlen):
        karte = Karte(self.inhalt, polster=18, radius=14)
        karte.pack(fill="x", padx=24, pady=(10, 6))
        innen = karte.innen

        kopf = tk.Frame(innen, bg=KARTE)
        kopf.pack(fill="x")
        tk.Label(kopf, text="Termine und Fristen", bg=KARTE, fg=TEXT,
                 font=S_TITEL, anchor="w").pack(side="left")
        tk.Label(kopf, text="zählt neue und vorgemerkte Stellen · Klick öffnet die Liste",
                 bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN, anchor="e").pack(side="right")

        reihe = tk.Frame(innen, bg=KARTE)
        reihe.pack(fill="x", pady=(12, 0))
        for fach, beschriftung, farbe in AMPEL:
            eintraege = zahlen["fristen"][fach]
            feld = tk.Frame(reihe, bg=zart(farbe), cursor="hand2" if eintraege else "arrow")
            feld.pack(side="left", fill="both", expand=True, padx=3)
            oben = tk.Label(feld, text=str(len(eintraege)), bg=zart(farbe), fg=farbe,
                            font=(SCHRIFT, 20, "bold"))
            oben.pack(pady=(10, 0))
            unten = tk.Label(feld, text=beschriftung, bg=zart(farbe), fg=farbe,
                             font=S_KLEIN, wraplength=120)
            unten.pack(pady=(1, 10))
            if eintraege:
                for widget in (feld, oben, unten):
                    widget.bind("<Button-1>",
                                lambda e, f=fach: self.app.fristen_zeigen(f))

    def _naechste(self, zahlen):
        dringend = (zahlen["fristen"]["heute_morgen"] + zahlen["fristen"]["woche"]
                    + zahlen["fristen"]["zwei_wochen"])
        karte = Karte(self.inhalt, polster=18, radius=14)
        karte.pack(fill="x", padx=24, pady=(10, 6))
        innen = karte.innen
        tk.Label(innen, text="Das steht als Nächstes an", bg=KARTE, fg=TEXT,
                 font=S_TITEL, anchor="w").pack(fill="x")

        if not dringend:
            tk.Label(innen, text="Keine Stelle mit Frist in den nächsten zwei Wochen.",
                     bg=KARTE, fg=TEXT_LEISE, font=S_NORMAL, anchor="w").pack(
                fill="x", pady=(10, 0))
            return

        for zeile in dringend[:8]:
            text, fach = frist_text(zeile["frist"])
            farbe = AMPEL_FARBE[fach]
            reihe = tk.Frame(innen, bg=KARTE, cursor="hand2")
            reihe.pack(fill="x", pady=3)
            tk.Label(reihe, text=text, bg=KARTE, fg=farbe, width=24, anchor="w",
                     font=S_FETT).pack(side="left")
            marke(reihe, f"{zeile['punkte']} P", MINT).pack(side="left", padx=(0, 10))
            tk.Label(reihe, text=zeile["titel"][:68], bg=KARTE, fg=TEXT,
                     anchor="w", font=S_NORMAL).pack(side="left")
            tk.Label(reihe, text=f"  {(zeile['arbeitgeber'] or '')[:34]}", bg=KARTE,
                     fg=TEXT_LEISE, anchor="w", font=S_KLEIN).pack(side="left")
            for widget in (reihe,) + tuple(reihe.winfo_children()):
                widget.bind("<Button-1>",
                            lambda e, u=zeile["url"]: webbrowser.open(u))

    def _verteilung(self, zahlen):
        reihe = tk.Frame(self.inhalt, bg=FLAECHE)
        reihe.pack(fill="x", padx=20, pady=(10, 6))

        links = Karte(reihe, polster=18, radius=14)
        links.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(links.innen, text="Nach Berufsfeld", bg=KARTE, fg=TEXT,
                 font=S_TITEL, anchor="w").pack(fill="x", pady=(0, 10))
        hoechst = max(list(zahlen["felder"].values()) or [1])
        for nummer in sorted(eo.FELDER):
            self._zeile(links.innen, f"{eo.FELD_KURZ[nummer]} {eo.FELDER[nummer]}",
                        zahlen["felder"].get(nummer, 0), hoechst,
                        eo.FELD_FARBE.get(nummer, INDIGO))

        rechts = Karte(reihe, polster=18, radius=14)
        rechts.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(rechts.innen, text="Nach Bereich", bg=KARTE, fg=TEXT,
                 font=S_TITEL, anchor="w").pack(fill="x", pady=(0, 10))
        hoechst = max(list(zahlen["sektoren"].values()) or [1])
        for schluessel, name in eo.SEKTOREN.items():
            self._zeile(rechts.innen, name, zahlen["sektoren"].get(schluessel, 0),
                        hoechst, BLAU)

    def _zeile(self, eltern, beschriftung, anzahl, hoechst, farbe):
        reihe = tk.Frame(eltern, bg=KARTE)
        reihe.pack(fill="x", pady=3)
        tk.Label(reihe, text=beschriftung, bg=KARTE, fg=TEXT, width=34, anchor="w",
                 font=S_NORMAL).pack(side="left")
        tk.Label(reihe, text=str(anzahl), bg=KARTE, fg=TEXT_LEISE, width=4,
                 anchor="e", font=S_FETT).pack(side="left", padx=(0, 10))
        balken(reihe, anzahl / max(1, hoechst), farbe, breite=140).pack(side="left")

    def _letzter_lauf(self, zahlen):
        lauf = zahlen["letzter_lauf"]
        karte = Karte(self.inhalt, polster=14, radius=12)
        karte.pack(fill="x", padx=24, pady=(10, 24))
        if lauf and lauf["beendet"]:
            try:
                wann = datetime.fromisoformat(lauf["beendet"]).strftime("%d.%m.%Y, %H:%M")
            except ValueError:
                wann = lauf["beendet"]
            text = (f"Letzter Suchlauf: {wann}  ·  {lauf['gesehen']} Stellen geprüft, "
                    f"{lauf['neu']} neu aufgenommen, {lauf['verworfen']} nicht passend")
        else:
            text = ("Noch kein Suchlauf gelaufen. Oben rechts auf "
                    "„Suchlauf starten\" klicken.")
        tk.Label(karte.innen, text=text, bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN,
                 anchor="w").pack(fill="x")


# ----------------------------------------------------------------------------------
# ANSICHT: BERUFSFELDER UND PROFIL
# ----------------------------------------------------------------------------------

class BerufsfelderAnsicht(tk.Frame):
    """Berufsfelder ansehen und ändern — Stichworte und Kompetenzen.

    Die Stichworte entscheiden, was überhaupt gefunden wird. Die Kompetenzen
    sind die eigenen Belege aus dem Lebenslauf: was man in diesem Feld
    mitbringt.
    Nach einer Weiterbildung kommt hier eine Zeile dazu.
    """

    def __init__(self, eltern, app):
        super().__init__(eltern, bg=FLAECHE)
        self.app = app
        self.felder = {}
        self.gewaehlt = None
        self.profil = {}
        self._bauen()

    def _bauen(self):
        ueberschrift(self, "Berufsfelder und Profil",
                     "Die Stichworte entscheiden, welche Stellen gefunden werden. "
                     "Die Kompetenzen sind die Belege aus dem Lebenslauf.").pack(
            fill="x", padx=24, pady=(20, 14))

        koerper = tk.Frame(self, bg=FLAECHE)
        koerper.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Linke Spalte: Auswahl
        linkekarte = Karte(koerper, polster=12, radius=14)
        linkekarte.pack(side="left", fill="y", padx=4)
        halter = tk.Frame(linkekarte.innen, bg=KARTE, width=258)
        halter.pack(fill="both", expand=True)
        halter.pack_propagate(False)
        # Rollbar, weil sechs Felder plus Profil höher werden als das Fenster
        aussen, self.auswahl = rollbereich(halter, hintergrund=KARTE)
        aussen.pack(fill="both", expand=True)

        # Rechte Spalte: Bearbeitung
        self.rechts = Karte(koerper, polster=18, radius=14)
        self.rechts.pack(side="left", fill="both", expand=True, padx=4)

    def laden(self):
        self.felder = kfg.felder_laden()
        self.profil = kfg.profil_laden()
        self._auswahl_bauen()
        if self.gewaehlt is None:
            self.gewaehlt = sorted(self.felder)[0]
        self._bearbeitung_bauen()

    def _auswahl_bauen(self):
        for kind in self.auswahl.winfo_children():
            kind.destroy()
        tk.Label(self.auswahl, text="BEREICHE", bg=KARTE, fg=TEXT_LEISE,
                 font=(SCHRIFT, 8, "bold"), anchor="w").pack(fill="x", pady=(0, 8))

        for nummer in sorted(self.felder):
            feld = self.felder[nummer]
            self._eintrag(nummer, f"{feld.get('zeichen', '')} {feld['name']}",
                          feld.get("farbe", INDIGO),
                          f"{sum(len(w) for w in feld['stichworte'].values())} Stichworte · "
                          f"{len(feld.get('kompetenzen', []))} Kompetenzen")

        trenner(self.auswahl).pack(fill="x", pady=10)
        self._eintrag("profil", "👤 Mein Profil", VIOLETT,
                      f"{len(self.profil.get('weiterbildungen', []))} Weiterbildungen")

    def _eintrag(self, schluessel, beschriftung, farbe, unterzeile):
        aktiv = (self.gewaehlt == schluessel)
        hg = zart(farbe) if aktiv else KARTE
        reihe = tk.Frame(self.auswahl, bg=hg, cursor="hand2")
        reihe.pack(fill="x", pady=2)
        innen = tk.Frame(reihe, bg=hg)
        innen.pack(fill="x", padx=9, pady=7)
        tk.Label(innen, text=beschriftung, bg=hg, fg=farbe if aktiv else TEXT,
                 font=S_FETT if aktiv else S_NORMAL, anchor="w",
                 wraplength=230, justify="left").pack(fill="x")
        tk.Label(innen, text=unterzeile, bg=hg, fg=TEXT_LEISE, font=S_KLEIN,
                 anchor="w").pack(fill="x")
        for widget in (reihe, innen) + tuple(innen.winfo_children()):
            widget.bind("<Button-1>", lambda e, s=schluessel: self._waehlen(s))

    def _waehlen(self, schluessel):
        self.gewaehlt = schluessel
        self._auswahl_bauen()
        self._bearbeitung_bauen()

    # -- Rechte Seite --------------------------------------------------------
    def _bearbeitung_bauen(self):
        for kind in self.rechts.innen.winfo_children():
            kind.destroy()
        if self.gewaehlt == "profil":
            self._profil_bauen()
        else:
            self._feld_bauen()

    def _feld_bauen(self):
        innen = self.rechts.innen
        feld = self.felder[self.gewaehlt]
        farbe = feld.get("farbe", INDIGO)

        kopf = tk.Frame(innen, bg=KARTE)
        kopf.pack(fill="x")
        symbolplaettchen(kopf, feld.get("zeichen", "•"), farbe, 40).pack(side="left")
        namenbereich = tk.Frame(kopf, bg=KARTE)
        namenbereich.pack(side="left", padx=12, fill="x", expand=True)
        tk.Label(namenbereich, text="Bezeichnung", bg=KARTE, fg=TEXT_LEISE,
                 font=S_KLEIN, anchor="w").pack(fill="x")
        rahmen, self.name_feld = eingabe(namenbereich, breite=44)
        rahmen.pack(fill="x", pady=(2, 0))
        self.name_feld.insert(0, feld["name"])

        aussen, bereich = rollbereich(innen, hintergrund=KARTE)
        aussen.pack(fill="both", expand=True, pady=(14, 0))

        tk.Label(bereich, text="Stichworte — danach wird gesucht", bg=KARTE, fg=TEXT,
                 font=S_TITEL, anchor="w").pack(fill="x")
        tk.Label(bereich,
                 text="Ein Stichwort je Zeile, klein geschrieben. Wortstämme genügen: "
                      "„projektleit\" findet auch Projektleiterin und Projektleitung.\n"
                      "Je höher das Gewicht, desto mehr Punkte gibt der Treffer.",
                 bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN, anchor="w",
                 justify="left").pack(fill="x", pady=(2, 10))

        # Die drei Gewichtsstufen nebeneinander — untereinander wurde es zu eng
        self.stichwort_felder = {}
        spalten = tk.Frame(bereich, bg=KARTE)
        spalten.pack(fill="x")
        erklaerung = [("3", "Gewicht 3", "sehr aussagekräftig", MINT),
                      ("2", "Gewicht 2", "deutlich", GELB),
                      ("1", "Gewicht 1", "schwaches Signal", TEXT_LEISE)]
        for stufe, beschriftung, hinweis, stufenfarbe in erklaerung:
            spalte = tk.Frame(spalten, bg=KARTE)
            spalte.pack(side="left", fill="both", expand=True, padx=(0, 10))
            kopfzeile = tk.Frame(spalte, bg=KARTE)
            kopfzeile.pack(fill="x", pady=(0, 4))
            marke(kopfzeile, beschriftung, stufenfarbe).pack(side="left")
            tk.Label(kopfzeile, text=hinweis, bg=KARTE, fg=TEXT_LEISE,
                     font=S_KLEIN).pack(side="left", padx=6)
            rahmen, textbereich = textfeld(spalte, hoehe=9)
            rahmen.pack(fill="both", expand=True)
            textbereich.insert("1.0", "\n".join(feld["stichworte"].get(stufe, [])))
            self.stichwort_felder[stufe] = textbereich

        trenner(bereich).pack(fill="x", pady=8)

        tk.Label(bereich, text="Meine Kompetenzen in diesem Feld", bg=KARTE, fg=TEXT,
                 font=S_TITEL, anchor="w").pack(fill="x")
        tk.Label(bereich,
                 text="Belege aus dem Lebenslauf — eine je Zeile. Nach einer "
                      "Weiterbildung hier ergänzen.",
                 bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN, anchor="w").pack(
            fill="x", pady=(2, 8))
        rahmen, self.kompetenz_feld = textfeld(bereich, hoehe=8)
        rahmen.pack(fill="x")
        self.kompetenz_feld.insert("1.0", "\n".join(feld.get("kompetenzen", [])))

        self._knopfleiste(innen, self._feld_speichern)

    def _profil_bauen(self):
        innen = self.rechts.innen
        kopf = tk.Frame(innen, bg=KARTE)
        kopf.pack(fill="x")
        symbolplaettchen(kopf, "👤", VIOLETT, 40).pack(side="left")
        tk.Label(kopf, text=f"{self.profil.get('name', '')} · "
                            f"{self.profil.get('abschluss', '')}",
                 bg=KARTE, fg=TEXT, font=S_TITEL, anchor="w").pack(
            side="left", padx=12)

        aussen, bereich = rollbereich(innen, hintergrund=KARTE)
        aussen.pack(fill="both", expand=True, pady=(14, 0))

        self.profil_felder = {}
        abschnitte = [
            ("werdegang", "Werdegang",
             "Eine Station je Zeile. Grundlage für die Einschätzung der Stellen."),
            ("staerken", "Übergreifende Stärken",
             "Was unabhängig vom Berufsfeld zählt — eine je Zeile."),
            ("weiterbildungen", "Weiterbildungen und Zertifikate",
             "Hier eintragen, was neu dazukommt. Eine je Zeile."),
        ]
        for schluessel, beschriftung, hinweis in abschnitte:
            tk.Label(bereich, text=beschriftung, bg=KARTE, fg=TEXT, font=S_TITEL,
                     anchor="w").pack(fill="x", pady=(6, 0))
            tk.Label(bereich, text=hinweis, bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN,
                     anchor="w").pack(fill="x", pady=(2, 6))
            rahmen, feld = textfeld(bereich, hoehe=6)
            rahmen.pack(fill="x", pady=(0, 10))
            feld.insert("1.0", "\n".join(self.profil.get(schluessel, [])))
            self.profil_felder[schluessel] = feld

        self._knopfleiste(innen, self._profil_speichern)

    def _knopfleiste(self, eltern, speichern_befehl):
        leiste = tk.Frame(eltern, bg=KARTE)
        leiste.pack(fill="x", pady=(14, 0))
        knopf(leiste, "Speichern", speichern_befehl, MINT).pack(side="left")
        knopf(leiste, "Auf Auslieferungszustand zurücksetzen", self._zuruecksetzen,
              TEXT_LEISE, hell=True).pack(side="left", padx=8)
        bereich = "profil" if self.gewaehlt == "profil" else "felder"
        if kfg.ist_geaendert(bereich):
            tk.Label(leiste, text="● eigene Fassung", bg=KARTE, fg=GELB,
                     font=S_KLEIN).pack(side="right")

    def _zeilen(self, feld):
        return [z.strip() for z in feld.get("1.0", "end").splitlines() if z.strip()]

    def _feld_speichern(self):
        feld = self.felder[self.gewaehlt]
        name = self.name_feld.get().strip()
        if not name:
            messagebox.showwarning("Bezeichnung fehlt",
                                   "Ein Berufsfeld braucht eine Bezeichnung.")
            return
        feld["name"] = name
        for stufe, textbereich in self.stichwort_felder.items():
            feld["stichworte"][stufe] = [w.lower() for w in self._zeilen(textbereich)]
        feld["kompetenzen"] = self._zeilen(self.kompetenz_feld)
        kfg.felder_speichern(self.felder)
        eo.neu_laden()
        self.app.melden(f"Berufsfeld „{name}“ gespeichert. "
                        f"Die neuen Stichworte gelten ab dem nächsten Suchlauf.")
        self.app.alles_neu_laden()
        self._nachfiltern_anbieten()

    def _profil_speichern(self):
        for schluessel, feld in self.profil_felder.items():
            self.profil[schluessel] = self._zeilen(feld)
        kfg.profil_speichern(self.profil)
        self.app.melden("Profil gespeichert.")
        self.laden()

    def _zuruecksetzen(self):
        bereich = "profil" if self.gewaehlt == "profil" else "felder"
        name = "Profil" if bereich == "profil" else "alle Berufsfelder"
        if not messagebox.askyesno(
                "Zurücksetzen",
                f"{name} wieder auf den Auslieferungszustand bringen?\n\n"
                f"Eigene Änderungen gehen dabei verloren."):
            return
        kfg.zuruecksetzen(bereich)
        eo.neu_laden()
        self.laden()
        self.app.melden(f"{name} zurückgesetzt.")

    def _nachfiltern_anbieten(self):
        if not messagebox.askyesno(
                "Gespeicherte Stellen prüfen?",
                "Die geänderten Stichworte gelten ab dem nächsten Suchlauf.\n\n"
                "Sollen die bereits gefundenen Stellen jetzt noch einmal gegen "
                "die neuen Regeln geprüft werden?\n\n"
                "Angefasst wird nur, was auf „neu\" steht — Vorgemerktes, "
                "Beworbenes und bewusst Verworfenes bleibt unberührt."):
            return
        self.app.nachfiltern_starten()


# ----------------------------------------------------------------------------------
# ANSICHT: GEWICHTUNG
# ----------------------------------------------------------------------------------

class GewichtungAnsicht(tk.Frame):
    """Wie viele Punkte wofür. Der Regler zwischen Nähe und Entgelt."""

    def __init__(self, eltern, app):
        super().__init__(eltern, bg=FLAECHE)
        self.app = app
        self.gewichte = {}
        self.variablen = {}
        self.aussen, self.inhalt = rollbereich(self)
        self.aussen.pack(fill="both", expand=True)

    def laden(self):
        for kind in self.inhalt.winfo_children():
            kind.destroy()
        self.gewichte = kfg.gewichte_laden()
        self.variablen = {}

        ueberschrift(self.inhalt, "Gewichtung",
                     "Hier entscheidet sich, was eine Stelle „wert\" ist. Wer gerade "
                     "auf kurze Wege aus ist, dreht die Regionen hoch; wer aufs "
                     "Entgelt schaut, die Entgeltgruppen.").pack(
            fill="x", padx=24, pady=(20, 6))

        self._schnellwahl()
        self._grundsaetzliches()
        self._gruppe("regionen", "Nähe — Punkte je Region", MINT,
                     "Wo die Stelle liegt. Höhere Zahl = kurzer Weg zählt mehr.")
        self._gruppe("entgelt", "Bezahlung — Punkte je Entgeltgruppe", GELB,
                     "Negative Zahlen werten ab. E = Tarif, A = Besoldung.")
        self._gruppe("sektoren", "Punkte je Bereich", BLAU,
                     "Öffentlicher Dienst, Wissenschaft, Beratung, Privatwirtschaft.",
                     namen=eo.SEKTOREN)
        self._knoepfe()

    def _schnellwahl(self):
        karte = Karte(self.inhalt, polster=16, radius=14)
        karte.pack(fill="x", padx=24, pady=(8, 6))
        innen = karte.innen
        tk.Label(innen, text="Schnell umstellen", bg=KARTE, fg=TEXT, font=S_TITEL,
                 anchor="w").pack(fill="x")
        tk.Label(innen, text="Setzt die Zahlen unten auf eine Grundhaltung. "
                             "Danach lässt sich alles einzeln nachjustieren.",
                 bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN, anchor="w").pack(
            fill="x", pady=(2, 10))
        reihe = tk.Frame(innen, bg=KARTE)
        reihe.pack(fill="x")
        vorlagen = [
            ("🏠  Nähe ist wichtig", "naehe", MINT),
            ("💶  Bezahlung ist wichtig", "entgelt", GELB),
            ("🎯  Fachliche Passung zählt", "fachlich", INDIGO),
            ("⚖  Ausgewogen (Standard)", "standard", TEXT_LEISE),
        ]
        for beschriftung, schluessel, farbe in vorlagen:
            knopf(reihe, beschriftung, lambda s=schluessel: self._vorlage(s),
                  farbe, hell=True).pack(side="left", padx=(0, 8))

    def _vorlage(self, schluessel):
        """Setzt eine Grundhaltung. Danach kann man einzeln nachjustieren."""
        g = kfg.gewichte_laden()
        if schluessel == "naehe":
            g["regionen"] = {"Potsdam": 10, "Babelsberg": 10, "Potsdam-Mittelmark": 7,
                             "Werder": 6, "Teltow": 6, "Kleinmachnow": 6,
                             "Stahnsdorf": 6, "Berlin": 3, "Brandenburg": 1,
                             "Bundesweit": -3, "Sonstige": 0}
            g["entgelt"] = {k: max(-1, min(2, v)) for k, v in g["entgelt"].items()}
        elif schluessel == "entgelt":
            g["entgelt"] = {"E 9": -4, "E 10": -1, "E 11": 4, "E 12": 7, "E 13": 9,
                            "E 14": 10, "E 15": 8, "A 10": -4, "A 11": -1, "A 12": 4,
                            "A 13": 7, "A 14": 9, "A 15": 8}
            g["regionen"] = {k: min(3, v) for k, v in g["regionen"].items()}
        elif schluessel == "fachlich":
            g["berufsfeld_hoechstens"] = 16
            g["mehrere_felder"] = 4
            g["regionen"] = {k: min(3, v) for k, v in g["regionen"].items()}
            g["entgelt"] = {k: max(-1, min(2, v)) for k, v in g["entgelt"].items()}
        else:
            g = dict(kfg.STANDARD_GEWICHTE)
        kfg.gewichte_speichern(g)
        eo.neu_laden()
        self.laden()
        self.app.melden("Gewichtung umgestellt. "
                        "Jetzt „Punkte neu berechnen\" drücken.")

    def _grundsaetzliches(self):
        karte = Karte(self.inhalt, polster=16, radius=14)
        karte.pack(fill="x", padx=24, pady=(8, 6))
        innen = karte.innen
        tk.Label(innen, text="Grundsätzliches", bg=KARTE, fg=TEXT, font=S_TITEL,
                 anchor="w").pack(fill="x", pady=(0, 10))
        for schluessel in ("berufsfeld_hoechstens", "mehrere_felder", "unbefristet",
                           "befristet", "leitungsfunktion", "frist_vorhanden"):
            reihe = tk.Frame(innen, bg=KARTE)
            reihe.pack(fill="x", pady=4)
            rahmen, variable = zahlfeld(reihe, self.gewichte.get(schluessel, 0),
                                        von=-20, bis=30)
            rahmen.pack(side="left")
            self.variablen[("einfach", schluessel)] = variable
            tk.Label(reihe, text=kfg.GEWICHT_ERKLAERUNG.get(schluessel, schluessel),
                     bg=KARTE, fg=TEXT, font=S_NORMAL, anchor="w",
                     wraplength=760, justify="left").pack(side="left", padx=12)

    def _gruppe(self, schluessel, beschriftung, farbe, hinweis, namen=None):
        karte = Karte(self.inhalt, polster=16, radius=14)
        karte.pack(fill="x", padx=24, pady=(8, 6))
        innen = karte.innen
        kopf = tk.Frame(innen, bg=KARTE)
        kopf.pack(fill="x")
        symbolplaettchen(kopf, "●", farbe, 26).pack(side="left", padx=(0, 8))
        tk.Label(kopf, text=beschriftung, bg=KARTE, fg=TEXT, font=S_TITEL,
                 anchor="w").pack(side="left")
        tk.Label(innen, text=hinweis, bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN,
                 anchor="w").pack(fill="x", pady=(2, 10))

        raster = tk.Frame(innen, bg=KARTE)
        raster.pack(fill="x")
        eintraege = sorted(self.gewichte.get(schluessel, {}).items())
        spalten = 3
        for nummer, (name, wert) in enumerate(eintraege):
            zelle = tk.Frame(raster, bg=KARTE)
            zelle.grid(row=nummer // spalten, column=nummer % spalten,
                       sticky="w", padx=(0, 26), pady=3)
            rahmen, variable = zahlfeld(zelle, wert, von=-20, bis=20)
            rahmen.pack(side="left")
            self.variablen[(schluessel, name)] = variable
            anzeige = namen.get(name, name) if namen else name
            tk.Label(zelle, text=anzeige, bg=KARTE, fg=TEXT, font=S_NORMAL,
                     anchor="w", width=26).pack(side="left", padx=8)

    def _knoepfe(self):
        karte = Karte(self.inhalt, polster=16, radius=14)
        karte.pack(fill="x", padx=24, pady=(8, 24))
        leiste = karte.innen
        knopf(leiste, "Speichern und Punkte neu berechnen", self._speichern,
              MINT).pack(side="left")
        knopf(leiste, "Auf Standard zurücksetzen", self._zuruecksetzen, TEXT_LEISE,
              hell=True).pack(side="left", padx=8)
        if kfg.ist_geaendert("gewichte"):
            tk.Label(leiste, text="● eigene Fassung", bg=KARTE, fg=GELB,
                     font=S_KLEIN).pack(side="right")

    def _speichern(self):
        for (gruppe, name), variable in self.variablen.items():
            try:
                wert = int(variable.get())
            except (ValueError, tk.TclError):
                continue
            if gruppe == "einfach":
                self.gewichte[name] = wert
            else:
                self.gewichte.setdefault(gruppe, {})[name] = wert
        kfg.gewichte_speichern(self.gewichte)
        eo.neu_laden()
        self.app.melden("Gewichtung gespeichert, Punkte werden neu berechnet …")
        self.app.punkte_neu_berechnen()

    def _zuruecksetzen(self):
        if not messagebox.askyesno("Zurücksetzen",
                                   "Gewichtung auf den Standard zurücksetzen?"):
            return
        kfg.zuruecksetzen("gewichte")
        eo.neu_laden()
        self.laden()
        self.app.punkte_neu_berechnen()


# ----------------------------------------------------------------------------------
# ANSICHT: ARCHIV
# ----------------------------------------------------------------------------------

class ArchivAnsicht(tk.Frame):
    """Die gesicherten Ausschreibungsseiten."""

    def __init__(self, eltern, app):
        super().__init__(eltern, bg=FLAECHE)
        self.app = app
        self.aussen, self.inhalt = rollbereich(self)
        self.aussen.pack(fill="both", expand=True)

    def laden(self):
        for kind in self.inhalt.winfo_children():
            kind.destroy()
        info = archiv.uebersicht()
        ohne = db.ohne_archiv()

        ueberschrift(self.inhalt, "Archiv",
                     "Zu jeder Stelle wird die Originalseite als PDF gesichert. "
                     "Portale nehmen Ausschreibungen nach Fristende offline — "
                     "dann ist die Kopie das Einzige, was bleibt.").pack(
            fill="x", padx=24, pady=(20, 14))

        reihe = tk.Frame(self.inhalt, bg=FLAECHE)
        reihe.pack(fill="x", padx=20, pady=(0, 6))
        kacheln = [
            ("📑", "gesicherte Seiten", info["anzahl"], MINT),
            ("💾", "Speicherplatz", f"{info['groesse_mb']:.0f} MB", BLAU),
            ("⏳", "noch offen", len(ohne), GELB if ohne else TEXT_LEISE),
        ]
        for zeichen, name, wert, farbe in kacheln:
            karte = Karte(reihe, polster=16, radius=14)
            karte.pack(side="left", fill="both", expand=True, padx=4)
            kopf = tk.Frame(karte.innen, bg=KARTE)
            kopf.pack(fill="x")
            symbolplaettchen(kopf, zeichen, farbe, 34).pack(side="left")
            tk.Label(kopf, text=str(wert), bg=KARTE, fg=TEXT,
                     font=S_ZAHL).pack(side="right")
            tk.Label(karte.innen, text=name, bg=KARTE, fg=TEXT_LEISE, font=S_NORMAL,
                     anchor="w").pack(fill="x", pady=(8, 0))

        karte = Karte(self.inhalt, polster=16, radius=14)
        karte.pack(fill="x", padx=24, pady=(10, 6))
        innen = karte.innen
        tk.Label(innen, text="Ordner und Aktionen", bg=KARTE, fg=TEXT, font=S_TITEL,
                 anchor="w").pack(fill="x")
        tk.Label(innen, text=info["ordner"], bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN,
                 anchor="w").pack(fill="x", pady=(2, 10))
        leiste = tk.Frame(innen, bg=KARTE)
        leiste.pack(fill="x")
        knopf(leiste, "📂  Ordner öffnen",
              lambda: datei_oeffnen(archiv.ordner()), BLAU, hell=True).pack(side="left")
        if ohne:
            knopf(leiste, f"📑  {len(ohne)} offene Seiten jetzt sichern",
                  lambda: self.app.archivieren_starten([z["id"] for z in ohne]),
                  MINT).pack(side="left", padx=8)

        if ohne:
            karte = Karte(self.inhalt, polster=16, radius=14)
            karte.pack(fill="x", padx=24, pady=(10, 24))
            innen = karte.innen
            tk.Label(innen, text="Noch ohne Seitenkopie", bg=KARTE, fg=TEXT,
                     font=S_TITEL, anchor="w").pack(fill="x", pady=(0, 8))
            for zeile in ohne[:14]:
                reihe = tk.Frame(innen, bg=KARTE)
                reihe.pack(fill="x", pady=2)
                marke(reihe, f"{zeile['punkte']} P", GELB).pack(side="left",
                                                                padx=(0, 10))
                tk.Label(reihe, text=zeile["titel"][:66], bg=KARTE, fg=TEXT,
                         font=S_NORMAL, anchor="w").pack(side="left")
                tk.Label(reihe, text=f"  {(zeile['arbeitgeber'] or '')[:30]}",
                         bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN,
                         anchor="w").pack(side="left")
            if len(ohne) > 14:
                tk.Label(innen, text=f"… und {len(ohne) - 14} weitere", bg=KARTE,
                         fg=TEXT_LEISE, font=S_KLEIN, anchor="w").pack(
                    fill="x", pady=(6, 0))
        else:
            karte = Karte(self.inhalt, polster=16, radius=14)
            karte.pack(fill="x", padx=24, pady=(10, 24))
            tk.Label(karte.innen,
                     text="✓  Zu jeder Stelle liegt eine gesicherte Seite.",
                     bg=KARTE, fg=MINT, font=S_FETT, anchor="w").pack(fill="x")


# ----------------------------------------------------------------------------------
# ANSICHT: FAVORITEN
# ----------------------------------------------------------------------------------

class FavoritenAnsicht(tk.Frame):
    """Die ausgewählten Stellen mit Vorbereitungs-Briefing.

    Links durchschalten, rechts alles zu dieser Stelle: harte Eckdaten,
    Ansprechpartner, hinterlegte Kompetenzen — und darunter, was die lokale KI
    aus Ausschreibung und Profil zusammenträgt.

    Die Trennung ist Absicht: Die oberen Abschnitte stammen direkt aus der
    Ausschreibung und stimmen. Was die KI beisteuert, steht darunter und ist
    als solches gekennzeichnet.
    """

    def __init__(self, eltern, app):
        super().__init__(eltern, bg=FLAECHE)
        self.app = app
        self.zeilen = []
        self.gewaehlt = None
        self._bauen()

    def _bauen(self):
        self.kopfbereich = tk.Frame(self, bg=FLAECHE)
        self.kopfbereich.pack(fill="x", padx=24, pady=(16, 10))

        koerper = tk.Frame(self, bg=FLAECHE)
        koerper.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Links: Liste zum Durchschalten
        linkekarte = Karte(koerper, polster=12, radius=14)
        linkekarte.pack(side="left", fill="y", padx=4)
        halter = tk.Frame(linkekarte.innen, bg=KARTE, width=270)
        halter.pack(fill="both", expand=True)
        halter.pack_propagate(False)
        aussen, self.auswahl = rollbereich(halter, hintergrund=KARTE)
        aussen.pack(fill="both", expand=True)

        # Rechts: Briefing
        self.rechts = Karte(koerper, polster=16, radius=14)
        self.rechts.pack(side="left", fill="both", expand=True, padx=4)

    def laden(self):
        self.zeilen = db.favoriten()
        for kind in self.kopfbereich.winfo_children():
            kind.destroy()
        ueberschrift(self.kopfbereich, "Favoriten",
                     "Die Stellen, die wirklich infrage kommen — mit allem, was "
                     "für Anschreiben und Vorstellungsgespräch zählt.").pack(
            fill="x")

        kennungen = [z["id"] for z in self.zeilen]
        if self.gewaehlt not in kennungen:
            self.gewaehlt = kennungen[0] if kennungen else None
        self._auswahl_bauen()
        self._briefing_bauen()

    def _auswahl_bauen(self):
        for kind in self.auswahl.winfo_children():
            kind.destroy()
        tk.Label(self.auswahl, text=f"{len(self.zeilen)} FAVORITEN", bg=KARTE,
                 fg=TEXT_LEISE, font=(SCHRIFT, 8, "bold"), anchor="w").pack(
            fill="x", pady=(0, 8))

        if not self.zeilen:
            tk.Label(self.auswahl,
                     text="Noch keine Favoriten.\n\nIn einer Stellenliste eine Zeile "
                          "anklicken und auf „★ Favorit\" drücken.",
                     bg=KARTE, fg=TEXT_LEISE, font=S_NORMAL, anchor="w",
                     justify="left", wraplength=240).pack(fill="x")
            return

        for zeile in self.zeilen:
            aktiv = (zeile["id"] == self.gewaehlt)
            text, fach = frist_text(zeile["frist"])
            farbe = AMPEL_FARBE[fach]
            hg = zart(GELB) if aktiv else KARTE
            reihe = tk.Frame(self.auswahl, bg=hg, cursor="hand2")
            reihe.pack(fill="x", pady=2)
            innen = tk.Frame(reihe, bg=hg)
            innen.pack(fill="x", padx=9, pady=8)

            oben = tk.Frame(innen, bg=hg)
            oben.pack(fill="x")
            tk.Label(oben, text="★", bg=hg, fg=GELB,
                     font=(SCHRIFT, 10)).pack(side="left")
            tk.Label(oben, text=f"{zeile['punkte']} P", bg=hg, fg=MINT,
                     font=(SCHRIFT, 9, "bold")).pack(side="left", padx=6)
            fertig = bool(spaltenwert(zeile, "briefing"))
            tk.Label(oben, text="✓ aufbereitet" if fertig else "ohne Briefing",
                     bg=hg, fg=MINT if fertig else TEXT_LEISE,
                     font=S_KLEIN).pack(side="right")

            tk.Label(innen, text=zeile["titel"], bg=hg,
                     fg=TEXT if aktiv else TEXT, font=S_FETT if aktiv else S_NORMAL,
                     anchor="w", wraplength=236, justify="left").pack(
                fill="x", pady=(3, 0))
            tk.Label(innen, text=(zeile["arbeitgeber"] or "")[:40], bg=hg,
                     fg=TEXT_LEISE, font=S_KLEIN, anchor="w").pack(fill="x")
            tk.Label(innen, text=text, bg=hg, fg=farbe, font=S_KLEIN,
                     anchor="w").pack(fill="x")

            for widget in [reihe, innen, oben] + list(innen.winfo_children()) \
                    + list(oben.winfo_children()):
                widget.bind("<Button-1>", lambda e, k=zeile["id"]: self._waehlen(k))

    def _waehlen(self, kennung):
        self.gewaehlt = kennung
        self._auswahl_bauen()
        self._briefing_bauen()

    def _briefing_bauen(self):
        for kind in self.rechts.innen.winfo_children():
            kind.destroy()
        innen = self.rechts.innen

        if not self.gewaehlt:
            tk.Label(innen, text="Keine Stelle ausgewählt", bg=KARTE, fg=TEXT,
                     font=S_TITEL, anchor="w").pack(fill="x")
            tk.Label(innen,
                     text="Favoriten markierst du in den Stellenlisten mit dem "
                          "Stern. Hier erscheint dann zu jeder Stelle eine "
                          "Aufbereitung für Anschreiben und Gespräch.",
                     bg=KARTE, fg=TEXT_LEISE, font=S_NORMAL, anchor="w",
                     justify="left", wraplength=620).pack(fill="x", pady=(8, 0))
            return

        zeile = db.eine(self.gewaehlt)
        if not zeile:
            return

        # Kopf
        kopf = tk.Frame(innen, bg=KARTE)
        kopf.pack(fill="x")
        symbolplaettchen(kopf, "★", GELB, 40).pack(side="left")
        titelbereich = tk.Frame(kopf, bg=KARTE)
        titelbereich.pack(side="left", padx=12, fill="x", expand=True)
        tk.Label(titelbereich, text=zeile["titel"], bg=KARTE, fg=TEXT,
                 font=S_TITEL, anchor="w", wraplength=640, justify="left").pack(
            fill="x")
        tk.Label(titelbereich, text=zeile["arbeitgeber"] or "", bg=KARTE,
                 fg=TEXT_LEISE, font=S_NORMAL, anchor="w").pack(fill="x")

        # Marken
        markenreihe = tk.Frame(innen, bg=KARTE)
        markenreihe.pack(fill="x", pady=(10, 0))
        text, fach = frist_text(zeile["frist"])
        marke(markenreihe, text, AMPEL_FARBE[fach]).pack(side="left", padx=(0, 6))
        marke(markenreihe, f"{zeile['punkte']} Punkte", MINT).pack(side="left",
                                                                   padx=(0, 6))
        if zeile["entgelt"]:
            marke(markenreihe, zeile["entgelt"], VIOLETT).pack(side="left", padx=(0, 6))
        if zeile["ort"]:
            marke(markenreihe, zeile["ort"], BLAU).pack(side="left", padx=(0, 6))
        marke(markenreihe, db.STATUS_NAMEN.get(zeile["status"], ""),
              TEXT_LEISE).pack(side="left")

        # Briefing-Text
        briefingtext = spaltenwert(zeile, "briefing")
        rahmen, feld = textfeld(innen, hoehe=22)
        rahmen.pack(fill="both", expand=True, pady=(12, 0))
        feld.configure(font=("Consolas", 10))
        if briefingtext:
            feld.insert("1.0", briefingtext)
        else:
            feld.insert("1.0",
                        briefing_platzhalter(zeile))
        feld.configure(state="disabled")
        self.briefing_feld = feld

        # Fußleiste
        leiste = tk.Frame(innen, bg=KARTE)
        leiste.pack(fill="x", pady=(12, 0))
        # Zuerst der rechte Knopf: pack gibt dem zuletzt gepackten Element nur
        # noch den Rest — ohne das wird er bei schmalem Fenster abgeschnitten.
        knopf(leiste, "★  Entfernen", self._favorit_entfernen, GELB,
              hell=True).pack(side="right")
        knopf(leiste, "🧠  Mit KI aufbereiten",
              lambda: self.app.briefing_starten(self.gewaehlt, mit_ki=True),
              INDIGO).pack(side="left")
        knopf(leiste, "Eckdaten ohne KI",
              lambda: self.app.briefing_starten(self.gewaehlt, mit_ki=False),
              TEXT_LEISE, hell=True).pack(side="left", padx=8)
        knopf(leiste, "🌐  Im Browser",
              lambda: webbrowser.open(zeile["url"]), BLAU, hell=True).pack(
            side="left", padx=(0, 8))
        archivpfad = spaltenwert(zeile, "archiv_pdf")
        if archivpfad and os.path.exists(archivpfad):
            knopf(leiste, "📑  Seitenkopie",
                  lambda p=archivpfad: datei_oeffnen(p), KORALLE, hell=True).pack(
                side="left", padx=(0, 8))

        wann = spaltenwert(zeile, "briefing_am")
        if wann:
            modell = spaltenwert(zeile, "briefing_modell") or "?"
            try:
                lesbar = datetime.fromisoformat(wann).strftime("%d.%m.%Y, %H:%M")
            except ValueError:
                lesbar = wann
            tk.Label(innen, text=f"Aufbereitet am {lesbar} mit {modell}", bg=KARTE,
                     fg=TEXT_LEISE, font=S_KLEIN, anchor="w").pack(
                fill="x", pady=(8, 0))

    def _favorit_entfernen(self):
        db.favorit_setzen([self.gewaehlt], False)
        self.gewaehlt = None
        self.app.melden("Aus den Favoriten entfernt.")
        self.app.alles_neu_laden()


def briefing_platzhalter(zeile):
    import briefing as brf
    try:
        return (brf.grundgeruest(zeile)
                + "\n" + brf.TRENNER + "\n"
                + "Noch nicht aufbereitet.\n\n"
                + "„🧠 Mit KI aufbereiten\" ergänzt unten:\n"
                + "  ④ was die Stelle verlangt\n"
                + "  ⑤ wo die eigenen Kompetenzen passen\n"
                + "  ⑥ der Elefant im Raum — mögliche Lücken und wie man sie dreht\n"
                + "  ⑦ was über den Arbeitgeber bekannt ist\n"
                + "  ⑧ Fragen fürs Vorstellungsgespräch\n\n"
                + "Dafür muss Ollama laufen. Das Programm startet den Dienst "
                  "selbst, wenn er nicht läuft.")
    except Exception as fehler:
        return f"Eckdaten konnten nicht aufbereitet werden: {fehler}"


# ----------------------------------------------------------------------------------
# HAUPTFENSTER
# ----------------------------------------------------------------------------------

NAVIGATION = [
    ("dashboard", "▦", "Dashboard", INDIGO),
    ("trenner1", None, None, None),
    (db.NEU, "●", "Neu", BLAU),
    (db.VORGEMERKT, "★", "Vorgemerkt", MINT),
    (db.BEWORBEN, "✉", "Beworben", VIOLETT),
    (db.VERWORFEN, "✕", "Verworfen", TEXT_LEISE),
    ("trenner2", None, None, None),
    ("favoriten", "★", "Favoriten", GELB),
    ("berufsfelder", "◉", "Berufsfelder", TUERKIS),
    ("gewichtung", "◨", "Gewichtung", GELB),
    ("archiv", "▤", "Archiv", KORALLE),
]


class App:

    def __init__(self, wurzel):
        self.wurzel = wurzel
        self.warteschlange = queue.Queue()
        self.lauf = None
        self.laeuft = False
        self.aktuell = "dashboard"
        self.nav_elemente = {}

        # Der Name steht im Profil, nicht im Code.
        self.eigner = (kfg.profil_laden().get("name") or "").strip()
        wurzel.title(f"Stellenradar — {self.eigner}" if self.eigner
                     else "Stellenradar")
        wurzel.geometry("1480x940")
        wurzel.minsize(1200, 760)
        wurzel.configure(bg=FLAECHE)
        self._symbol()
        tabellenstil()

        db.einrichten()
        eo.neu_laden()
        # Tageskopie der Datenbank. Die Triage ist Handarbeit — Status, Notizen,
        # Favoriten und Briefings stecken nur hier.
        try:
            db.sichern()
        except Exception:
            pass

        self._fuss()            # zuerst, damit er unten bleibt
        self._kopf()
        self._koerper()
        self.zeigen("dashboard")

    def _symbol(self):
        pfad = os.path.join(BASIS, "stellenradar.ico")
        if os.path.exists(pfad):
            try:
                self.wurzel.iconbitmap(pfad)
            except Exception:
                pass

    # -- Kopfzeile -----------------------------------------------------------
    def _kopf(self):
        kopf = tk.Frame(self.wurzel, bg=KARTE, height=82)
        kopf.pack(side="top", fill="x")
        kopf.pack_propagate(False)

        links = tk.Frame(kopf, bg=KARTE)
        links.pack(side="left", padx=22)
        symbolplaettchen(links, "📡", INDIGO, 40).pack(side="left", pady=21)
        beschriftung = tk.Frame(links, bg=KARTE)
        beschriftung.pack(side="left", padx=11)
        tk.Label(beschriftung, text="Stellenradar", bg=KARTE, fg=TEXT,
                 font=S_GROSS, anchor="w").pack(fill="x", pady=(18, 0))
        tk.Label(beschriftung, text="Öffentlicher Dienst und Public-Sector-Beratung · "
                                    "Berlin, Potsdam und Umgebung",
                 bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN, anchor="w").pack(fill="x")

        rechts = tk.Frame(kopf, bg=KARTE)
        rechts.pack(side="right", padx=18)
        self.knopf_suche = knopf(rechts, "🔍  Suchlauf starten", self.suchlauf_starten,
                                 INDIGO, breit=True)
        self.knopf_suche.pack(side="left", pady=22, padx=4)
        self.knopf_stopp = tk.Button(
            rechts, text="⏹  Stopp", command=self.suchlauf_stoppen, bg=zart(ROT),
            fg=ROT, activebackground=zart(ROT), activeforeground=ROT, relief="flat",
            bd=0, font=S_FETT, padx=13, pady=8, cursor="hand2", state="disabled")
        self.knopf_stopp.pack(side="left", padx=4)
        knopf(rechts, "＋  Stelle erfassen", self.stelle_erfassen, MINT,
              hell=True).pack(side="left", padx=4)
        knopf(rechts, "📑  Dossier", self.dossier, VIOLETT, hell=True).pack(
            side="left", padx=4)
        knopf(rechts, "⚙", self.einstellungen_zeigen, TEXT_LEISE, hell=True).pack(
            side="left", padx=4)

    # -- Fußzeile ------------------------------------------------------------
    def _fuss(self):
        fuss = tk.Frame(self.wurzel, bg=KARTE, height=46)
        fuss.pack(side="bottom", fill="x")
        fuss.pack_propagate(False)
        self.statuszeile = tk.Label(fuss, text="Bereit.", anchor="w", bg=KARTE,
                                    fg=TEXT_LEISE, font=S_KLEIN)
        self.statuszeile.pack(side="bottom", fill="x", padx=22, pady=(0, 10))
        # Der Balken erscheint nur, solange etwas laeuft — ein leerer Trog sieht
        # sonst aus wie ein defekter Rollbalken.
        self.balken = ttk.Progressbar(fuss, mode="determinate",
                                      style="Radar.Horizontal.TProgressbar")

    # -- Seitenleiste und Inhalt ---------------------------------------------
    def _koerper(self):
        koerper = tk.Frame(self.wurzel, bg=FLAECHE)
        koerper.pack(fill="both", expand=True)

        leiste = tk.Frame(koerper, bg=SEITE, width=222)
        leiste.pack(side="left", fill="y")
        leiste.pack_propagate(False)
        self._navigation(leiste)

        self.inhaltsbereich = tk.Frame(koerper, bg=FLAECHE)
        self.inhaltsbereich.pack(side="left", fill="both", expand=True)

        self.ansichten = {
            "dashboard": DashboardAnsicht(self.inhaltsbereich, self),
            "berufsfelder": BerufsfelderAnsicht(self.inhaltsbereich, self),
            "gewichtung": GewichtungAnsicht(self.inhaltsbereich, self),
            "archiv": ArchivAnsicht(self.inhaltsbereich, self),
            "favoriten": FavoritenAnsicht(self.inhaltsbereich, self),
        }
        for status in (db.NEU, db.VORGEMERKT, db.BEWORBEN, db.VERWORFEN):
            self.ansichten[status] = ListenAnsicht(self.inhaltsbereich, self, status)

    def _navigation(self, leiste):
        tk.Label(leiste, text="NAVIGATION", bg=SEITE, fg="#6B7599",
                 font=(SCHRIFT, 8, "bold"), anchor="w").pack(
            fill="x", padx=20, pady=(20, 10))

        for schluessel, zeichen, beschriftung, farbe in NAVIGATION:
            if zeichen is None:
                tk.Frame(leiste, bg=SEITE_HELL, height=1).pack(
                    fill="x", padx=18, pady=9)
                continue
            reihe = tk.Frame(leiste, bg=SEITE, cursor="hand2")
            reihe.pack(fill="x", padx=12, pady=1)
            innen = tk.Frame(reihe, bg=SEITE)
            innen.pack(fill="x", padx=10, pady=8)
            symbol = tk.Label(innen, text=zeichen, bg=SEITE, fg=farbe,
                              font=(SCHRIFT, 12))
            symbol.pack(side="left")
            name = tk.Label(innen, text=beschriftung, bg=SEITE, fg="#C9CFE4",
                            font=S_MITTEL, anchor="w")
            name.pack(side="left", padx=10)
            zaehler = tk.Label(innen, text="", bg=SEITE, fg="#6B7599", font=S_KLEIN)
            zaehler.pack(side="right")
            self.nav_elemente[schluessel] = (reihe, innen, symbol, name, zaehler)
            for widget in (reihe, innen, symbol, name, zaehler):
                widget.bind("<Button-1>", lambda e, s=schluessel: self.zeigen(s))

        # Fußbereich der Seitenleiste
        fuss = tk.Frame(leiste, bg=SEITE)
        fuss.pack(side="bottom", fill="x", pady=16)
        tk.Label(fuss, text=(f"Stellenradar · {self.eigner}" if self.eigner
                             else "Stellenradar"),
                 bg=SEITE,
                 fg="#4C5578", font=(SCHRIFT, 8), anchor="w").pack(
            fill="x", padx=20)

    def _navigation_auffrischen(self):
        kennzahlen = db.kennzahlen()
        zahlen = kennzahlen["status"]
        for schluessel, element in self.nav_elemente.items():
            reihe, innen, symbol, name, zaehler = element
            aktiv = (schluessel == self.aktuell)
            hg = SEITE_AKTIV if aktiv else SEITE
            for widget in (reihe, innen, symbol, name, zaehler):
                widget.configure(bg=hg)
            name.configure(fg=TEXT_HELL if aktiv else "#C9CFE4",
                           font=(SCHRIFT, 11, "bold") if aktiv else S_MITTEL)
            if aktiv:
                symbol.configure(fg=TEXT_HELL)
            else:
                farbe = dict((s, f) for s, _, _, f in NAVIGATION if f).get(
                    schluessel, TEXT_LEISE)
                symbol.configure(fg=farbe)
            if schluessel in zahlen:
                zaehler.configure(text=str(zahlen.get(schluessel, 0)),
                                  fg=TEXT_HELL if aktiv else "#6B7599")
            elif schluessel == "favoriten":
                zaehler.configure(text=str(kennzahlen.get("favoriten", 0)),
                                  fg=TEXT_HELL if aktiv else "#6B7599")

    # -- Umschalten ----------------------------------------------------------
    def zeigen(self, schluessel):
        if schluessel not in self.ansichten:
            return
        for ansicht in self.ansichten.values():
            ansicht.pack_forget()
        self.aktuell = schluessel
        ansicht = self.ansichten[schluessel]
        ansicht.pack(fill="both", expand=True)
        ansicht.laden()
        self._navigation_auffrischen()

    def fristen_zeigen(self, fach):
        self.zeigen(db.NEU)
        liste = self.ansichten[db.NEU]
        liste.sortier_wahl.set("Frist zuerst")
        liste.laden()
        beschriftung = dict((f, b) for f, b, _ in AMPEL)[fach]
        self.melden(f"Liste nach Frist sortiert — gesucht war „{beschriftung}“.")

    def alles_neu_laden(self):
        self.ansichten[self.aktuell].laden()
        self._navigation_auffrischen()

    def melden(self, text):
        self.statuszeile.config(text=text)

    # -- Einstellungen -------------------------------------------------------
    def einstellungen_zeigen(self):
        fenster = tk.Toplevel(self.wurzel)
        fenster.title("Einstellungen für den Suchlauf")
        fenster.configure(bg=FLAECHE)
        fenster.geometry("560x380")
        fenster.transient(self.wurzel)

        karte = Karte(fenster, polster=18, radius=14)
        karte.pack(fill="both", expand=True, padx=16, pady=16)
        innen = karte.innen
        tk.Label(innen, text="Suchlauf", bg=KARTE, fg=TEXT, font=S_TITEL,
                 anchor="w").pack(fill="x", pady=(0, 12))

        for variable, beschriftung, hinweis in (
                (self.gruendlich, "Gründlich suchen",
                 "Prüft auch Stellen mit nichtssagendem Titel. Findet mehr, "
                 "dauert deutlich länger."),
                (self.mit_interamt, "Interamt durchsuchen",
                 "Umkreissuche um Potsdam — die wichtigste Quelle."),
                (self.mit_berlin, "Karriereportal Berlin durchsuchen",
                 "Senatsverwaltungen, Bezirksämter und nachgeordnete Behörden — "
                 "rund 630 Stellen."),
                (self.mit_seiten, "Arbeitgeberseiten durchsuchen",
                 "Die 93 geprüften Karriereseiten."),
                (self.mit_archiv, "Seiten automatisch als PDF sichern",
                 "Nach dem Lauf wird jede neue Ausschreibungsseite archiviert.")):
            zeile = tk.Frame(innen, bg=KARTE)
            zeile.pack(fill="x", pady=5)
            tk.Checkbutton(zeile, variable=variable, bg=KARTE, fg=TEXT,
                           activebackground=KARTE, selectcolor="#FBFCFE",
                           font=S_FETT, text=beschriftung, anchor="w",
                           bd=0, highlightthickness=0).pack(fill="x")
            tk.Label(zeile, text=hinweis, bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN,
                     anchor="w", wraplength=460, justify="left").pack(
                fill="x", padx=24)

        zeile = tk.Frame(innen, bg=KARTE)
        zeile.pack(fill="x", pady=(12, 0))
        rahmen, _ = zahlfeld(zeile, self.runden.get(), von=1, bis=90)
        rahmen.pack(side="left")
        # Das Zahlfeld bekommt die vorhandene Variable, damit der Wert hängen bleibt
        rahmen.winfo_children()[0].configure(textvariable=self.runden)
        tk.Label(zeile, text="Interamt-Nachladerunden (je Runde 10 Stellen)",
                 bg=KARTE, fg=TEXT, font=S_NORMAL, anchor="w").pack(
            side="left", padx=12)
        tk.Label(innen,
                 text="Interamt hatte zuletzt rund 830 Stellen im Umkreis. 25 Runden "
                      "lesen davon etwa 260 — das genügt für den laufenden Betrieb, "
                      "weil die Liste nach Einstelldatum sortiert ist und Neues oben "
                      "steht. Beim ersten Lauf lohnt es sich, auf 85 zu stellen; das "
                      "dauert dann rund eine Viertelstunde länger.",
                 bg=KARTE, fg=TEXT_LEISE, font=S_KLEIN, anchor="w",
                 wraplength=470, justify="left").pack(fill="x", padx=24, pady=(4, 0))

        knopf(innen, "Schließen", fenster.destroy, INDIGO).pack(
            side="bottom", anchor="e", pady=(14, 0))

    # -- Hintergrundarbeiten -------------------------------------------------
    def steckbriefe_erzeugen(self, kennungen):
        if self.laeuft:
            self.melden("Erst den laufenden Vorgang abwarten.")
            return
        self._beschaeftigt(f"Erzeuge {len(kennungen)} Steckbrief(e) …")

        def arbeit():
            erzeugt, fehler = sb.steckbriefe_erzeugen(
                kennungen, melden=lambda t: self.warteschlange.put(("hinweis", t)))
            self.warteschlange.put(("pdf_fertig", erzeugt, fehler))

        self._starten(arbeit)

    def archivieren_starten(self, kennungen):
        if self.laeuft:
            self.melden("Erst den laufenden Vorgang abwarten.")
            return
        self._beschaeftigt(f"Sichere {len(kennungen)} Ausschreibungsseite(n) …")

        def arbeit():
            gesichert, uebersprungen, fehler = archiv.fehlende_archivieren(
                kennungen, melden=lambda t: self.warteschlange.put(("hinweis", t)))
            self.warteschlange.put(("archiv_fertig", gesichert, fehler))

        self._starten(arbeit)

    def stelle_erfassen(self):
        ErfassenDialog(self.wurzel, self)

    def abgelaufene_aufraeumen(self):
        """Bietet an, Stellen mit abgelaufener Frist zu verwerfen."""
        alt = db.abgelaufene(db.NEU)
        if not alt:
            self.melden("Keine abgelaufenen Stellen in der Liste.")
            return
        namen = "\n".join(f"  · {datum_de(z['frist'])}  {z['titel'][:56]}"
                          for z in alt[:12])
        if len(alt) > 12:
            namen += f"\n  … und {len(alt) - 12} weitere"
        if not messagebox.askyesno(
                "Abgelaufene Stellen",
                f"{len(alt)} Stellen sind abgelaufen und stehen noch auf „neu“:\n\n"
                f"{namen}\n\n"
                f"Jetzt verwerfen? Dabei werden auch ihre Steckbriefe und "
                f"Seitenkopien gelöscht."):
            return
        db.status_setzen([z["id"] for z in alt], db.VERWORFEN)
        self.melden(f"{len(alt)} abgelaufene Stellen verworfen.")
        self.alles_neu_laden()

    def dossier(self):
        if self.laeuft:
            self.melden("Erst den laufenden Vorgang abwarten.")
            return
        self._beschaeftigt("Erzeuge Dossier …")

        def arbeit():
            try:
                pfad, anzahl = sb.dossier_erzeugen()
                self.warteschlange.put(("dossier_fertig", pfad, anzahl))
            except Exception as fehler:
                self.warteschlange.put(("dossier_fehler", str(fehler)))

        self._starten(arbeit)

    def briefing_starten(self, kennung, mit_ki=True):
        """Bereitet eine favorisierte Stelle auf. Mit KI dauert das Minuten."""
        if self.laeuft:
            self.melden("Erst den laufenden Vorgang abwarten.")
            return
        import briefing as brf

        if not mit_ki:
            try:
                brf.erzeugen(kennung, nur_grundgeruest=True)
                self.melden("Eckdaten aufbereitet.")
            except Exception as fehler:
                messagebox.showwarning("Briefing", str(fehler))
            self.alles_neu_laden()
            return

        self._beschaeftigt("Starte die lokale KI …")

        def arbeit():
            import ki
            try:
                if not ki.erreichbar():
                    self.warteschlange.put(
                        ("hinweis", "Ollama läuft nicht — versuche zu starten …"))
                    if not ki.starten():
                        raise ki.KiFehler(
                            "Ollama konnte nicht gestartet werden. Bitte Ollama "
                            "über das Startmenü öffnen und noch einmal versuchen.")
                text, modell = brf.erzeugen(
                    kennung, melden=lambda m: self.warteschlange.put(("hinweis", m)))
                self.warteschlange.put(("briefing_fertig", modell, None))
            except Exception as fehler:
                self.warteschlange.put(("briefing_fertig", None, str(fehler)))

        self._starten(arbeit)

    def punkte_neu_berechnen(self):
        if self.laeuft:
            self.melden("Erst den laufenden Vorgang abwarten.")
            return
        self._beschaeftigt("Berechne die Punkte neu …")

        def arbeit():
            import suche
            ergebnis = suche.punkte_neu(
                melden=lambda t: self.warteschlange.put(("hinweis", t)))
            self.warteschlange.put(("punkte_fertig", ergebnis))

        self._starten(arbeit)

    def nachfiltern_starten(self):
        if self.laeuft:
            self.melden("Erst den laufenden Vorgang abwarten.")
            return
        self._beschaeftigt("Prüfe die gespeicherten Stellen …")

        def arbeit():
            import suche
            ergebnis = suche.nachfiltern(
                melden=lambda t: self.warteschlange.put(("hinweis", t)))
            self.warteschlange.put(("nachfilter_fertig", ergebnis))

        self._starten(arbeit)

    def _balken_zeigen(self):
        if not self.balken.winfo_ismapped():
            self.balken.pack(side="top", fill="x", padx=22, pady=(9, 2))

    def _beschaeftigt(self, text):
        self.laeuft = True
        self.melden(text)
        self._balken_zeigen()
        self.balken.config(mode="indeterminate")
        self.balken.start(12)
        self.knopf_suche.config(state="disabled")

    def _starten(self, arbeit):
        threading.Thread(target=arbeit, daemon=True).start()
        self.wurzel.after(150, self._warteschlange_pruefen)

    def _fertig(self):
        self.laeuft = False
        self.balken.stop()
        self.balken.config(mode="determinate", value=0)
        self.balken.pack_forget()
        self.knopf_suche.config(state="normal", text="🔍  Suchlauf starten")
        self.knopf_stopp.config(state="disabled")

    # -- Suchlauf ------------------------------------------------------------
    def suchlauf_starten(self):
        if self.laeuft:
            return
        if not (self.mit_interamt.get() or self.mit_seiten.get()
                or self.mit_berlin.get()):
            self.melden("Mindestens eine Quelle einschalten (Zahnrad oben rechts).")
            return
        self.laeuft = True
        self.knopf_suche.config(state="disabled", text="🔍  Suche läuft …")
        self.knopf_stopp.config(state="normal")
        self._balken_zeigen()
        self.balken.config(mode="determinate", value=0)

        import suche
        self.lauf = suche.Lauf(
            melden=lambda t: self.warteschlange.put(("hinweis", t)),
            fortschritt=lambda getan, gesamt:
                self.warteschlange.put(("fortschritt", getan, gesamt)),
            gruendlich=self.gruendlich.get(),
            interamt_runden=self.runden.get(),
            mit_archiv=self.mit_archiv.get())

        mit_interamt = self.mit_interamt.get()
        mit_seiten = self.mit_seiten.get()
        mit_berlin = self.mit_berlin.get()

        def arbeit():
            ergebnis = self.lauf.starten(mit_interamt=mit_interamt,
                                         mit_arbeitgebern=mit_seiten,
                                         mit_berlin=mit_berlin)
            self.warteschlange.put(("lauf_fertig", ergebnis))

        self._starten(arbeit)

    def suchlauf_stoppen(self):
        if self.lauf:
            self.lauf.abbrechen = True
            self.melden("Abbruch angefordert — der laufende Abruf wird noch beendet.")

    # -- Nachrichten aus dem Nebenthread --------------------------------------
    def _warteschlange_pruefen(self):
        fertig = False
        try:
            while True:
                nachricht = self.warteschlange.get_nowait()
                art = nachricht[0]
                if art == "hinweis":
                    self.melden(nachricht[1])
                elif art == "fortschritt":
                    self.balken.config(mode="determinate",
                                       maximum=max(1, nachricht[2]),
                                       value=nachricht[1])
                elif art == "lauf_fertig":
                    fertig = True
                    self._lauf_abschliessen(nachricht[1])
                elif art == "pdf_fertig":
                    fertig = True
                    self._fertig()
                    self.alles_neu_laden()
                    self._pdf_melden(nachricht[1], nachricht[2], "Steckbrief")
                elif art == "archiv_fertig":
                    fertig = True
                    self._fertig()
                    self.alles_neu_laden()
                    self._pdf_melden(nachricht[1], nachricht[2], "Seitenkopie")
                elif art == "dossier_fertig":
                    fertig = True
                    self._fertig()
                    pfad, anzahl = nachricht[1], nachricht[2]
                    self.melden(f"Dossier mit {anzahl} Stellen erzeugt.")
                    if messagebox.askyesno("Dossier fertig",
                                           f"Dossier mit {anzahl} Stellen:\n\n"
                                           f"{os.path.basename(pfad)}\n\nJetzt öffnen?"):
                        datei_oeffnen(pfad)
                elif art == "dossier_fehler":
                    fertig = True
                    self._fertig()
                    self.melden("Dossier konnte nicht erzeugt werden.")
                    messagebox.showwarning("Dossier", nachricht[1])
                elif art == "briefing_fertig":
                    fertig = True
                    self._fertig()
                    modell, fehler = nachricht[1], nachricht[2]
                    self.alles_neu_laden()
                    if fehler:
                        self.melden("Die KI konnte nicht aufbereiten.")
                        messagebox.showwarning("Briefing", fehler)
                    else:
                        self.melden(f"Briefing fertig (Modell: {modell}).")
                elif art == "punkte_fertig":
                    fertig = True
                    self._fertig()
                    self.alles_neu_laden()
                    ergebnis = nachricht[1]
                    self.melden(f"Punkte neu berechnet: {ergebnis['geaendert']} von "
                                f"{ergebnis['geprueft']} Stellen haben jetzt einen "
                                f"anderen Wert.")
                elif art == "nachfilter_fertig":
                    fertig = True
                    self._fertig()
                    self.alles_neu_laden()
                    ergebnis = nachricht[1]
                    self.melden(f"{ergebnis['geprueft']} geprüft, "
                                f"{ergebnis['aussortiert']} nachträglich aussortiert, "
                                f"{ergebnis['neu_bewertet']} neu bewertet.")
        except queue.Empty:
            pass
        if not fertig and self.laeuft:
            self.wurzel.after(150, self._warteschlange_pruefen)

    def _pdf_melden(self, erzeugt, fehler, was):
        if erzeugt and not fehler:
            self.melden(f"{len(erzeugt)} {was}(n) erzeugt.")
            if len(erzeugt) == 1:
                if messagebox.askyesno(f"{was} fertig",
                                       f"{os.path.basename(erzeugt[0])}\n\nJetzt öffnen?"):
                    datei_oeffnen(erzeugt[0])
            elif messagebox.askyesno(f"{was}e fertig",
                                     f"{len(erzeugt)} Dateien erzeugt.\n\nOrdner öffnen?"):
                datei_oeffnen(os.path.dirname(erzeugt[0]))
        else:
            self.melden(f"{len(erzeugt)} erzeugt, {len(fehler)} fehlgeschlagen.")
            if fehler:
                messagebox.showwarning(was, "\n".join(fehler[:10]))

    def _lauf_abschliessen(self, ergebnis):
        self.lauf = None
        self._fertig()
        self.alles_neu_laden()
        text = (f"{'Abgebrochen' if ergebnis['abgebrochen'] else 'Fertig'}: "
                f"{ergebnis['gesehen']} geprüft, {ergebnis['neu']} neu, "
                f"{ergebnis['aktualisiert']} aufgefrischt, "
                f"{ergebnis['verworfen']} nicht passend, "
                f"{ergebnis.get('archiviert', 0)} Seiten archiviert "
                f"({ergebnis['dauer'] / 60:.1f} Minuten).")
        self.melden(text)
        if ergebnis["neu"]:
            self.zeigen(db.NEU)
        if ergebnis["fehler"]:
            messagebox.showinfo(
                "Suchlauf beendet",
                f"{text}\n\nNicht erreichbar waren:\n\n"
                + "\n".join(ergebnis["fehler"][:12])
                + ("\n…" if len(ergebnis["fehler"]) > 12 else ""))


# Einstellungen als Klassenvariablen anlegen, damit sie den Dialog überleben
def _einstellungen_vorbereiten(app):
    app.gruendlich = tk.BooleanVar(value=False)
    app.mit_interamt = tk.BooleanVar(value=True)
    app.mit_seiten = tk.BooleanVar(value=True)
    app.mit_archiv = tk.BooleanVar(value=True)
    app.runden = tk.IntVar(value=25)


_urspruenglich = App.__init__


def _init_mit_einstellungen(self, wurzel):
    self.gruendlich = tk.BooleanVar(master=wurzel, value=False)
    self.mit_interamt = tk.BooleanVar(master=wurzel, value=True)
    self.mit_seiten = tk.BooleanVar(master=wurzel, value=True)
    self.mit_berlin = tk.BooleanVar(master=wurzel, value=True)
    self.mit_archiv = tk.BooleanVar(master=wurzel, value=True)
    self.runden = tk.IntVar(master=wurzel, value=25)
    _urspruenglich(self, wurzel)


App.__init__ = _init_mit_einstellungen


# ----------------------------------------------------------------------------------
# SELBSTTESTS
# ----------------------------------------------------------------------------------

def selftest():
    import tempfile
    ordner = tempfile.mkdtemp(prefix="radar_selftest_")
    db.DB_PFAD = os.path.join(ordner, "test.db")
    db.PDF_ORDNER = os.path.join(ordner, "steckbriefe")
    db.einrichten()

    fehler = 0

    def pruefe(bedingung, was):
        nonlocal fehler
        if not bedingung:
            fehler += 1
        print(f"[{'OK  ' if bedingung else 'FEHL'}] {was}")

    from datetime import timedelta
    heute = date.today()
    for frist, soll in [
            (None, "ohne"),
            ((heute - timedelta(days=2)).isoformat(), "abgelaufen"),
            (heute.isoformat(), "heute_morgen"),
            ((heute + timedelta(days=1)).isoformat(), "heute_morgen"),
            ((heute + timedelta(days=5)).isoformat(), "woche"),
            ((heute + timedelta(days=12)).isoformat(), "zwei_wochen"),
            ((heute + timedelta(days=40)).isoformat(), "spaeter")]:
        _, fach = frist_text(frist)
        pruefe(fach == soll, f"Fristen-Fach für {frist or 'ohne Frist'}: {fach}")

    pruefe(set(f for f, _, _ in AMPEL) == set(db.kennzahlen()["fristen"]),
           "Ampel-Fächer und Datenbank-Fächer stimmen überein")
    pruefe(all(s in db.STATUS_NAMEN for s in db.STATUS_REIHE),
           "alle Status haben einen Anzeigenamen")

    # Gewichtung wirkt wirklich
    probe = {"titel": "Referentin (m/w/d) Digitalisierung", "felder": [1],
             "feld_punkte": 7, "region": "Berlin", "sektor": "oed_be",
             "entgelt": "E 11", "befristung": "unbefristet"}
    standard = eo.punkte_berechnen(probe, kfg.STANDARD_GEWICHTE)[0]
    nah = dict(kfg.STANDARD_GEWICHTE)
    nah["regionen"] = dict(nah["regionen"], Berlin=0)
    weniger = eo.punkte_berechnen(probe, nah)[0]
    pruefe(weniger < standard,
           f"Region abwerten senkt die Punkte ({standard} → {weniger})")
    reich = dict(kfg.STANDARD_GEWICHTE)
    reich["entgelt"] = dict(reich["entgelt"])
    reich["entgelt"]["E 11"] = 12
    mehr = eo.punkte_berechnen(probe, reich)[0]
    pruefe(mehr > standard,
           f"Entgelt aufwerten hebt die Punkte ({standard} → {mehr})")

    # Konfiguration
    felder = kfg.felder_laden()
    pruefe(len(felder) == 6, f"{len(felder)} Berufsfelder geladen")
    pruefe(all("kompetenzen" in f for f in felder.values()),
           "jedes Berufsfeld hat ein Feld fuer Kompetenzen".replace("fuer", "für"))
    # Ohne eigenes Profil sind die Kompetenzen leer — das ist der
    # Auslieferungsstand, kein Fehler. Das KI-Briefing braucht sie aber.
    mit_belegen = sum(1 for f in felder.values() if f.get("kompetenzen"))
    if mit_belegen:
        pruefe(True, f"{mit_belegen} von 6 Berufsfeldern mit eigenen Belegen")
    else:
        print("[HINWEIS] Noch keine eigenen Kompetenzen hinterlegt — das "
              "KI-Briefing bleibt ohne Belege.")
        print("          Im Fenster unter „Berufsfelder“ eintragen.")
    profil = kfg.profil_laden()
    pruefe("weiterbildungen" in profil, "Profil kennt Weiterbildungen")

    print(f"\nSelbsttest: {'BESTANDEN' if fehler == 0 else str(fehler) + ' FEHLER'}")
    return fehler


def guitest():
    import tempfile
    from datetime import timedelta
    ordner = tempfile.mkdtemp(prefix="radar_guitest_")
    db.DB_PFAD = os.path.join(ordner, "test.db")
    db.PDF_ORDNER = os.path.join(ordner, "steckbriefe")
    archiv.ARCHIV_ORDNER = os.path.join(ordner, "archiv")
    db.einrichten()

    heute = date.today()
    proben = [
        ("https://t/1", "Referentin (m/w/d) Digitalisierung", "MIK", "oed_bb",
         "Potsdam", [1, 4], 24, (heute + timedelta(days=1)).isoformat(), db.NEU),
        ("https://t/2", "Projektleitung (m/w/d) E-Government", "ITDZ Berlin",
         "oed_be", "Berlin", [3, 1], 19, (heute + timedelta(days=6)).isoformat(),
         db.VORGEMERKT),
        ("https://t/3", "Prozessmanagement (m/w/d)", "PD", "beratung", "Berlin",
         [4], 16, None, db.BEWORBEN),
        ("https://t/4", "Nicht passend (m/w/d)", "X", "privat", "Berlin", [5], 7,
         (heute - timedelta(days=4)).isoformat(), db.VERWORFEN),
    ]
    for url, titel, ag, sektor, ort, felder, punkte, frist, _ in proben:
        db.speichern(dict(url=url, titel=titel, arbeitgeber=ag, quelle="Test",
                          sektor=sektor, region=ort, ort=ort, felder=felder,
                          feld_haupt=felder[0], punkte=punkte, frist=frist,
                          volltext="Beispieltext der Ausschreibung. " * 12))
    for nummer, (*_, status) in enumerate(proben, start=1):
        db.status_setzen([nummer], status)

    wurzel = tk.Tk()
    wurzel.withdraw()
    app = App(wurzel)
    wurzel.update()

    fehler = 0

    def pruefe(bedingung, was):
        nonlocal fehler
        if not bedingung:
            fehler += 1
        print(f"[{'OK  ' if bedingung else 'FEHL'}] {was}")

    pruefe(len(app.ansichten) == 9, f"{len(app.ansichten)} Ansichten angelegt")
    pruefe(app.aktuell == "dashboard", "startet im Dashboard")

    # Listen
    app.zeigen(db.NEU)
    wurzel.update()
    liste = app.ansichten[db.NEU]
    pruefe(len(liste.tabelle.get_children()) == 1, "Reiter Neu zeigt eine Stelle")
    liste.suchfeld.insert(0, "Digital")
    liste.laden()
    pruefe(len(liste.tabelle.get_children()) == 1, "Suchfeld filtert")
    liste.suchfeld.delete(0, "end")
    liste.sektor_wahl.set(eo.SEKTOREN["beratung"])
    liste.laden()
    pruefe(len(liste.tabelle.get_children()) == 0, "Bereichsfilter wirkt")
    liste.sektor_wahl.set("alle")
    liste.laden()

    # Triage
    liste.tabelle.selection_set(liste.tabelle.get_children())
    liste.status_setzen(db.VORGEMERKT)
    app.zeigen(db.VORGEMERKT)
    wurzel.update()
    pruefe(len(app.ansichten[db.VORGEMERKT].tabelle.get_children()) == 2,
           "Vormerken verschiebt in die richtige Ansicht")

    # Berufsfelder
    app.zeigen("berufsfelder")
    wurzel.update()
    felder = app.ansichten["berufsfelder"]
    pruefe(felder.gewaehlt == 1 or felder.gewaehlt == "1",
           f"Berufsfeld-Ansicht hat eine Auswahl ({felder.gewaehlt})")
    pruefe(hasattr(felder, "kompetenz_feld"), "Kompetenzen sind bearbeitbar")
    felder._waehlen("profil")
    wurzel.update()
    pruefe(hasattr(felder, "profil_felder") and "weiterbildungen" in felder.profil_felder,
           "Profil-Ansicht kennt Weiterbildungen")

    # Gewichtung
    app.zeigen("gewichtung")
    wurzel.update()
    gewichtung = app.ansichten["gewichtung"]
    pruefe(("regionen", "Potsdam") in gewichtung.variablen,
           "Regionen sind einzeln einstellbar")
    pruefe(("entgelt", "E 13") in gewichtung.variablen,
           "Entgeltgruppen sind einzeln einstellbar")
    pruefe(("einfach", "unbefristet") in gewichtung.variablen,
           "Grundsätzliches ist einstellbar")

    # Favoriten
    app.zeigen(db.VORGEMERKT)
    wurzel.update()
    liste = app.ansichten[db.VORGEMERKT]
    liste.tabelle.selection_set(liste.tabelle.get_children()[0])
    liste.favorit_umschalten()
    pruefe(len(db.favoriten()) == 1, "Stern macht eine Stelle zum Favoriten")
    app.zeigen("favoriten")
    wurzel.update()
    favoriten = app.ansichten["favoriten"]
    pruefe(len(favoriten.zeilen) == 1, "Favoriten-Ansicht zeigt die Stelle")
    pruefe(favoriten.gewaehlt is not None, "eine Stelle ist ausgewählt")
    pruefe(hasattr(favoriten, "briefing_feld"), "Briefing-Feld ist da")
    inhalt = favoriten.briefing_feld.get("1.0", "end")
    pruefe("KEY FACTS" in inhalt, "Eckdaten stehen im Briefing")
    pruefe("Noch nicht aufbereitet" in inhalt,
           "ohne KI steht der Hinweis auf die Aufbereitung")
    favoriten._favorit_entfernen()
    pruefe(len(db.favoriten()) == 0, "Favorit lässt sich wieder entfernen")

    # Beim Verwerfen werden die Dokumente geloescht
    import tempfile as tf
    probe = os.path.join(ordner, "probe_steckbrief.pdf")
    probe2 = os.path.join(ordner, "probe_archiv.pdf")
    for pfad in (probe, probe2):
        with open(pfad, "wb") as datei:
            datei.write(b"%PDF-1.4 Test")
    db.pdf_merken(1, probe)
    db.archiv_merken(1, probe2)
    db.status_setzen([1], db.VERWORFEN)
    pruefe(not os.path.exists(probe) and not os.path.exists(probe2),
           "Verwerfen löscht Steckbrief und archivierte Seite")
    zeile = db.eine(1)
    pruefe(not zeile["pdf_pfad"] and not zeile["archiv_pdf"],
           "die Pfade sind danach leer")

    # Bewerbungsverlauf
    db.verlauf_setzen(3, beworben_am="2026-11-01", rueckmeldung="Eingangsbestätigung",
                      wiedervorlage="2026-11-01")
    zeile = db.eine(3)
    pruefe(zeile["beworben_am"] == "2026-11-01", "Bewerbungsdatum wird gespeichert")
    pruefe(zeile["rueckmeldung"] == "Eingangsbestätigung", "Rückmeldung wird gespeichert")
    pruefe(len(db.wiedervorlagen()) >= 1, "fällige Wiedervorlage wird gefunden")

    app.zeigen(db.BEWORBEN)
    wurzel.update()
    liste = app.ansichten[db.BEWORBEN]
    pruefe(any(s[0] == "beworben_am" for s in liste.SPALTEN),
           "Beworben-Ansicht zeigt den Verlauf")

    # Volltextsuche und Abgelaufen-Erkennung mit einer eigenen Probe, damit die
    # Pruefung nicht vom Zustand der vorherigen Schritte abhaengt.
    db.speichern(dict(url="https://t/probe", titel="Probestelle (m/w/d)",
                      arbeitgeber="Testamt", quelle="Test", sektor="oed_bb",
                      region="Potsdam", ort="Potsdam", felder=[1], feld_haupt=1,
                      punkte=10, frist=(heute - timedelta(days=5)).isoformat(),
                      volltext="Besonderes Schluesselwort Wackelpudding im Text."))
    pruefe(len(db.holen(suche="Wackelpudding")) == 1,
           "Suche greift auch auf den Ausschreibungstext zu")
    pruefe(any(z["titel"].startswith("Probestelle") for z in db.abgelaufene(db.NEU)),
           "abgelaufene Stellen werden gefunden")

    # Von Hand erfassen
    import erfassen
    kennung, ist_neu, _ = erfassen.aus_text(
        "Referentin (m/w/d) Digitalisierung von Hand",
        "Steuerung von Digitalisierungsvorhaben und Prozessoptimierung in der "
        "Verwaltung. Anforderungsmanagement gegenüber dem IT-Dienstleister. " * 4,
        arbeitgeber="Stadt Teltow", sektor="oed_bb", ort="Teltow")
    pruefe(ist_neu, "von Hand erfasste Stelle wird angelegt")
    zeile = db.eine(kennung)
    pruefe(zeile["manuell"] == 1, "sie ist als von Hand erfasst markiert")
    pruefe(zeile["quelle"] == "von Hand", "Quelle steht auf „von Hand“")

    # Sicherung
    pfad = db.sichern()
    pruefe(pfad and os.path.exists(pfad), f"Sicherung angelegt: {os.path.basename(pfad or '')}")

    # Archiv
    app.zeigen("archiv")
    wurzel.update()
    pruefe(app.ansichten["archiv"].inhalt.winfo_children(), "Archiv-Ansicht baut auf")

    app.zeigen("dashboard")
    wurzel.update()
    pruefe(app.ansichten["dashboard"].inhalt.winfo_children(), "Dashboard baut auf")

    wurzel.destroy()
    print(f"\nGUI-Test: {'BESTANDEN' if fehler == 0 else str(fehler) + ' FEHLER'} "
          f"(Wegwerf-Datenbank: {db.DB_PFAD})")
    return fehler


# ----------------------------------------------------------------------------------
# START
# ----------------------------------------------------------------------------------

def _fehler_festhalten(ausnahme_text):
    """Schreibt einen Absturz in fehler.log und zeigt ihn, wenn möglich.

    Beim Start über pythonw.exe gibt es kein Konsolenfenster — ohne diese
    Aufzeichnung verschwindet das Programm wortlos."""
    try:
        with open(FEHLERPROTOKOLL, "a", encoding="utf-8") as datei:
            datei.write(f"\n{'=' * 70}\n"
                        f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                        f"Python: {sys.executable}\nOrdner: {os.getcwd()}\n"
                        f"{'=' * 70}\n{ausnahme_text}\n")
    except Exception:
        pass
    try:
        notfenster = tk.Tk()
        notfenster.withdraw()
        messagebox.showerror("Stellenradar konnte nicht starten",
                             f"{ausnahme_text.strip().splitlines()[-1]}\n\n"
                             f"Einzelheiten: {FEHLERPROTOKOLL}")
        notfenster.destroy()
    except Exception:
        pass


def _stdout_vorbereiten():
    """Sorgt dafür, dass es stdout und stderr überhaupt gibt.

    Beim Start über `pythonw.exe` aus einer Batchdatei hat der Prozess keine
    Konsole, und sys.stdout ist None. Genau daran ist das Programm einmal
    wortlos gestorben. Und es bliebe gefährlich: Scrapling schreibt beim
    Suchlauf Protokollzeilen nach stdout — ohne Ziel würde der Lauf abbrechen."""
    if sys.stdout is None or sys.stderr is None:
        try:
            ziel = open(LAUFPROTOKOLL, "a", encoding="utf-8", buffering=1)
        except Exception:
            import io
            ziel = io.StringIO()
        if sys.stdout is None:
            sys.stdout = ziel
        if sys.stderr is None:
            sys.stderr = ziel
        return
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(encoding="utf-8")
        except Exception:
            pass


def main():
    dpi_beachten()
    wurzel = tk.Tk()
    App(wurzel)
    wurzel.mainloop()


if __name__ == "__main__":
    _stdout_vorbereiten()
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--guitest" in sys.argv:
        sys.exit(guitest())
    try:
        main()
    except Exception:
        import traceback
        _fehler_festhalten(traceback.format_exc())
        sys.exit(1)
