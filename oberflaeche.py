# -*- coding: utf-8 -*-
"""Bausteine der Oberfläche: Farben, Karten, Marken, Knöpfe.

Das Aussehen folgt der Vorlage: helle Fläche, weiße Karten mit runden Ecken,
dunkle Seitenleiste, farbige Symbolplättchen, viel Luft. Tkinter kann von Haus
aus keine runden Ecken — die `Karte` zeichnet sie deshalb auf eine Leinwand
hinter dem Inhalt.
"""

import tkinter as tk
from tkinter import ttk

# ----------------------------------------------------------------------------------
# FARBEN
# ----------------------------------------------------------------------------------

FLAECHE = "#F4F7FC"        # heller Seitenhintergrund
KARTE = "#FFFFFF"
LINIE = "#E4EAF4"
SEITE = "#1E2749"          # dunkle Seitenleiste
SEITE_HELL = "#2C3860"
SEITE_AKTIV = "#5B63E8"

TEXT = "#1F2437"
TEXT_LEISE = "#8A90A6"
TEXT_HELL = "#FFFFFF"

INDIGO = "#5B63E8"
VIOLETT = "#8B5CF6"
BLAU = "#3B82F6"
TUERKIS = "#06B6D4"
MINT = "#10B981"
GELB = "#F59E0B"
KORALLE = "#F2663C"
ROT = "#E5484D"

# Hintergründe für farbige Plättchen
ZART = {
    INDIGO: "#EEF0FE", VIOLETT: "#F3EDFE", BLAU: "#EAF2FE", TUERKIS: "#E6F8FB",
    MINT: "#E7F8F1", GELB: "#FEF4E3", KORALLE: "#FDEEE9", ROT: "#FDECEC",
    TEXT_LEISE: "#F0F2F7",
}

SCHRIFT = "Segoe UI"
S_KLEIN = (SCHRIFT, 9)
S_NORMAL = (SCHRIFT, 10)
S_MITTEL = (SCHRIFT, 11)
S_FETT = (SCHRIFT, 10, "bold")
S_TITEL = (SCHRIFT, 13, "bold")
S_GROSS = (SCHRIFT, 17, "bold")
S_ZAHL = (SCHRIFT, 24, "bold")


def zart(farbe):
    return ZART.get(farbe, "#F0F2F7")


# ----------------------------------------------------------------------------------
# KARTE MIT RUNDEN ECKEN
# ----------------------------------------------------------------------------------

class Karte(tk.Frame):
    """Weiße Karte mit abgerundeten Ecken.

    Aufbau: Eine Leinwand liegt über die ganze Fläche (place) und zeichnet das
    gerundete Rechteck. Der Inhalt sitzt in `.innen` und wird mit einem Polster
    eingerückt, das mindestens so groß ist wie der Eckradius — sonst würden die
    eckigen Inhaltsflächen die runden Ecken wieder überdecken.
    """

    def __init__(self, eltern, hintergrund=FLAECHE, fuellung=KARTE,
                 radius=14, polster=16, rand=LINIE, **kw):
        super().__init__(eltern, bg=hintergrund, highlightthickness=0, bd=0, **kw)
        self._radius = radius
        self._fuellung = fuellung
        self._rand = rand
        self._leinwand = tk.Canvas(self, bg=hintergrund, highlightthickness=0, bd=0)
        self._leinwand.place(x=0, y=0, relwidth=1, relheight=1)
        self.innen = tk.Frame(self, bg=fuellung)
        self.innen.pack(fill="both", expand=True,
                        padx=max(polster, radius), pady=max(polster, radius))
        self.bind("<Configure>", self._zeichnen)

    def _zeichnen(self, ereignis=None):
        self._leinwand.delete("all")
        breite, hoehe = self.winfo_width(), self.winfo_height()
        if breite < 6 or hoehe < 6:
            return
        r = min(self._radius, breite // 2 - 1, hoehe // 2 - 1)
        x1, y1, x2, y2 = 1, 1, breite - 2, hoehe - 2
        punkte = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        self._leinwand.create_polygon(punkte, smooth=True, splinesteps=24,
                                      fill=self._fuellung,
                                      outline=self._rand or self._fuellung, width=1)

    def farbe_setzen(self, fuellung=None, rand=None):
        if fuellung:
            self._fuellung = fuellung
            self.innen.configure(bg=fuellung)
        if rand:
            self._rand = rand
        self._zeichnen()


# ----------------------------------------------------------------------------------
# KLEINE BAUSTEINE
# ----------------------------------------------------------------------------------

def marke(eltern, text, farbe=INDIGO, hintergrund=None, fett=True):
    """Farbiges Plättchen, etwa für Berufsfeld oder Frist."""
    rahmen = tk.Frame(eltern, bg=hintergrund or zart(farbe))
    tk.Label(rahmen, text=text, bg=hintergrund or zart(farbe), fg=farbe,
             font=(SCHRIFT, 9, "bold") if fett else S_KLEIN,
             padx=8, pady=3).pack()
    return rahmen


def symbolplaettchen(eltern, zeichen, farbe, groesse=38, hintergrund=KARTE):
    """Rundes, farbiges Quadrat mit einem Zeichen darin — wie in der Vorlage."""
    leinwand = tk.Canvas(eltern, width=groesse, height=groesse, bg=hintergrund,
                         highlightthickness=0, bd=0)
    r = groesse // 4
    x1, y1, x2, y2 = 1, 1, groesse - 2, groesse - 2
    punkte = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
              x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    leinwand.create_polygon(punkte, smooth=True, splinesteps=20,
                            fill=zart(farbe), outline=zart(farbe))
    leinwand.create_text(groesse / 2, groesse / 2 + 1, text=zeichen, fill=farbe,
                         font=(SCHRIFT, int(groesse * 0.42)))
    return leinwand


def knopf(eltern, text, befehl, farbe=INDIGO, hell=False, hintergrund=KARTE,
          breit=False):
    """Flacher Knopf. `hell=True` ergibt die zurückhaltende Zweitfassung."""
    if hell:
        vg, hg, aktiv = farbe, zart(farbe), zart(farbe)
    else:
        vg, hg, aktiv = TEXT_HELL, farbe, farbe
    element = tk.Button(
        eltern, text=text, command=befehl, bg=hg, fg=vg,
        activebackground=aktiv, activeforeground=vg, relief="flat", bd=0,
        font=S_FETT, cursor="hand2",
        padx=18 if breit else 13, pady=8 if breit else 6)

    def rein(_):
        try:
            element.configure(bg=_abdunkeln(hg, 0.93))
        except tk.TclError:
            pass

    def raus(_):
        try:
            element.configure(bg=hg)
        except tk.TclError:
            pass

    element.bind("<Enter>", rein)
    element.bind("<Leave>", raus)
    return element


def _abdunkeln(farbe, faktor):
    farbe = farbe.lstrip("#")
    r, g, b = (int(farbe[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * faktor), int(g * faktor), int(b * faktor))


def ueberschrift(eltern, text, unterzeile=None, hintergrund=FLAECHE):
    rahmen = tk.Frame(eltern, bg=hintergrund)
    tk.Label(rahmen, text=text, bg=hintergrund, fg=TEXT, font=S_GROSS,
             anchor="w").pack(fill="x")
    if unterzeile:
        tk.Label(rahmen, text=unterzeile, bg=hintergrund, fg=TEXT_LEISE,
                 font=S_NORMAL, anchor="w", justify="left").pack(fill="x", pady=(2, 0))
    return rahmen


def trenner(eltern, hintergrund=KARTE):
    return tk.Frame(eltern, bg=LINIE, height=1)


def balken(eltern, anteil, farbe=INDIGO, breite=150, hoehe=8, hintergrund=KARTE):
    """Schlanker Fortschrittsbalken mit runden Enden."""
    leinwand = tk.Canvas(eltern, width=breite, height=hoehe, bg=hintergrund,
                         highlightthickness=0, bd=0)
    r = hoehe / 2
    leinwand.create_oval(0, 0, hoehe, hoehe, fill="#EDF0F7", outline="#EDF0F7")
    leinwand.create_oval(breite - hoehe, 0, breite, hoehe, fill="#EDF0F7",
                         outline="#EDF0F7")
    leinwand.create_rectangle(r, 0, breite - r, hoehe, fill="#EDF0F7",
                              outline="#EDF0F7")
    gefuellt = max(hoehe, int(breite * max(0.0, min(1.0, anteil))))
    if anteil > 0:
        leinwand.create_oval(0, 0, hoehe, hoehe, fill=farbe, outline=farbe)
        leinwand.create_oval(gefuellt - hoehe, 0, gefuellt, hoehe, fill=farbe,
                             outline=farbe)
        leinwand.create_rectangle(r, 0, max(r, gefuellt - r), hoehe, fill=farbe,
                                  outline=farbe)
    return leinwand


def rollbereich(eltern, hintergrund=FLAECHE):
    """Scrollbarer Bereich. Gibt (aussen, innen) zurück — Inhalt kommt in innen."""
    aussen = tk.Frame(eltern, bg=hintergrund)
    leinwand = tk.Canvas(aussen, bg=hintergrund, highlightthickness=0, bd=0)
    leiste = ttk.Scrollbar(aussen, orient="vertical", command=leinwand.yview,
                           style="Radar.Vertical.TScrollbar")
    leinwand.configure(yscrollcommand=leiste.set)
    leiste.pack(side="right", fill="y")
    leinwand.pack(side="left", fill="both", expand=True)

    innen = tk.Frame(leinwand, bg=hintergrund)
    fenster = leinwand.create_window((0, 0), window=innen, anchor="nw")
    innen.bind("<Configure>",
               lambda e: leinwand.configure(scrollregion=leinwand.bbox("all")))
    leinwand.bind("<Configure>",
                  lambda e: leinwand.itemconfigure(fenster, width=e.width))

    def rollen(ereignis):
        leinwand.yview_scroll(int(-ereignis.delta / 120), "units")

    # Mausrad nur, solange der Zeiger über dem Bereich steht
    leinwand.bind("<Enter>", lambda e: leinwand.bind_all("<MouseWheel>", rollen))
    leinwand.bind("<Leave>", lambda e: leinwand.unbind_all("<MouseWheel>"))
    return aussen, innen


def textfeld(eltern, hoehe=8, hintergrund="#FBFCFE", breite=1):
    """Mehrzeiliges Eingabefeld mit Rollbalken, im Kartenstil.

    `breite=1` ist Absicht: Ein Text-Widget fordert sonst 80 Zeichen Breite an.
    Stehen mehrere nebeneinander, bekommt das erste alles und die übrigen
    werden aus dem Fenster gedrängt. Mit Breite 1 verteilt `pack` gleichmäßig,
    die tatsächliche Breite kommt über fill/expand.
    """
    rahmen = tk.Frame(eltern, bg=LINIE, highlightthickness=0, bd=0)
    innen = tk.Frame(rahmen, bg=hintergrund)
    innen.pack(fill="both", expand=True, padx=1, pady=1)
    feld = tk.Text(innen, height=hoehe, width=breite, wrap="word", font=S_NORMAL,
                   relief="flat", bg=hintergrund, fg=TEXT, bd=0, padx=8, pady=6,
                   insertbackground=INDIGO)
    leiste = ttk.Scrollbar(innen, orient="vertical", command=feld.yview,
                           style="Radar.Vertical.TScrollbar")
    feld.configure(yscrollcommand=leiste.set)
    leiste.pack(side="right", fill="y")
    feld.pack(side="left", fill="both", expand=True)
    return rahmen, feld


def eingabe(eltern, breite=24, hintergrund="#FBFCFE"):
    rahmen = tk.Frame(eltern, bg=LINIE)
    feld = tk.Entry(rahmen, width=breite, font=S_NORMAL, relief="flat", bd=0,
                    bg=hintergrund, fg=TEXT, insertbackground=INDIGO)
    feld.pack(fill="both", expand=True, padx=1, pady=1, ipady=5, ipadx=6)
    return rahmen, feld


def zahlfeld(eltern, wert, von=-20, bis=20, breite=5):
    rahmen = tk.Frame(eltern, bg=LINIE)
    variable = tk.IntVar(value=int(wert))
    feld = tk.Spinbox(rahmen, from_=von, to=bis, width=breite, textvariable=variable,
                      font=S_NORMAL, relief="flat", bd=0, bg="#FBFCFE", fg=TEXT,
                      buttonbackground="#EDF0F7", justify="center")
    feld.pack(fill="both", expand=True, padx=1, pady=1, ipady=3)
    return rahmen, variable


def tabellenstil():
    """Einheitliches Aussehen für alle Tabellen."""
    stil = ttk.Style()
    try:
        stil.theme_use("clam")
    except tk.TclError:
        pass
    stil.configure("Radar.Treeview", rowheight=30, font=S_NORMAL,
                   background=KARTE, fieldbackground=KARTE, foreground=TEXT,
                   borderwidth=0)
    stil.configure("Radar.Treeview.Heading", font=(SCHRIFT, 9, "bold"),
                   foreground=TEXT_LEISE, background="#F7F9FD",
                   relief="flat", padding=(6, 7))
    stil.map("Radar.Treeview.Heading", background=[("active", "#EDF1F9")])
    stil.map("Radar.Treeview",
             background=[("selected", "#E8EAFE")],
             foreground=[("selected", TEXT)])
    stil.configure("Radar.Vertical.TScrollbar", background="#DDE3EF",
                   troughcolor=FLAECHE, borderwidth=0, arrowsize=12)
    # Trog in Kartenfarbe: Im Ruhezustand soll der Balken nicht wie ein
    # leerer Rollbalken aussehen, sondern gar nicht auffallen.
    stil.configure("Radar.Horizontal.TProgressbar", background=INDIGO,
                   troughcolor=KARTE, borderwidth=0, thickness=5,
                   lightcolor=INDIGO, darkcolor=INDIGO)
    return stil
