# -*- coding: utf-8 -*-
"""Alles, was sich ohne Programmierkenntnisse ändern lassen soll.

Drei Bereiche, jeweils als JSON-Datei neben dem Programm. Fehlt eine Datei,
gilt der eingebaute Standard; ein Knopf in der Oberfläche stellt ihn wieder her.

  berufsfelder.json   Die sechs Berufsfelder: Name, Stichworte, Kompetenzen
  gewichtung.json     Wie viele Punkte wofür vergeben werden
  profil.json         Werdegang und übergreifende Stärken

Warum nicht im Code? Weil sich beides ändert: Nach einer Weiterbildung kommt
eine Kompetenz dazu, und je nach Lebenslage zählt mal die Nähe mehr, mal das
Entgelt. Beides soll man im Fenster ändern können, nicht in einer .py-Datei.
"""

import copy
import json
import os

BASIS = os.path.dirname(os.path.abspath(__file__))
FELDER_DATEI = os.path.join(BASIS, "berufsfelder.json")
GEWICHTE_DATEI = os.path.join(BASIS, "gewichtung.json")
PROFIL_DATEI = os.path.join(BASIS, "profil.json")


# ----------------------------------------------------------------------------------
# 1 · BERUFSFELDER
#
# stichworte: nach Gewicht gruppiert. 3 = sehr aussagekräftig („e-government"),
# 2 = deutlich, 1 = schwaches Signal. Das Gewicht geht in die Punkte ein.
# kompetenzen: die eigenen Belege aus dem Lebenslauf — was man in diesem Feld
#   mitbringt. Hier absichtlich leer: diese Liste gehört in die eigene
#   berufsfelder.json und wird im Fenster unter „Berufsfelder" gepflegt.
#   Sie geht in das KI-Briefing der Favoriten ein.
# ----------------------------------------------------------------------------------

STANDARD_FELDER = {
    "1": {
        "name": "Digitalisierung & E-Government",
        "zeichen": "①",
        "farbe": "#6366F1",
        "stichworte": {
            "3": ["e-government", "egovernment", "verwaltungsdigitalisier", "ozg",
                  "onlinezugangsgesetz", "registermodernisier", "digitalisierungsbeauftragt",
                  "digitale verwaltung", "verwaltungsmodernisier"],
            "2": ["digitalisierung", "digitalstrategie", "digitale transformation",
                  "e-akte", "eakte", "dokumentenmanagementsystem", "digitaler arbeitsplatz",
                  "it-strategie", "it-steuerung", "it-koordinat", "smart city", "smart-city",
                  "digitalisierungsprojekt", "fachverfahren", "digitallabor"],
            "1": ["onlinedienst", "open data", "datenstrategie", "it-architektur",
                  "informationssicherheitsmanag", "cio-", "digitalbüro"],
        },
        "kompetenzen": [],
    },
    "2": {
        "name": "IT-Produkt- & Anforderungsmanagement",
        "zeichen": "②",
        "farbe": "#8B5CF6",
        "stichworte": {
            "3": ["anforderungsmanag", "requirements engineer", "requirement engineer",
                  "product owner", "produktmanag", "produktverantwort", "product manag"],
            "2": ["produktstrateg", "product ownership", "it-portfolio", "portfoliomanag",
                  "release-manag", "releasemanag", "anwendungsbetreu", "fachverfahrensbetreu",
                  "dienstleistersteuerung", "it-dienstleistersteuerung"],
            "1": ["scrum master", "agile coach", "agile master", "business analyst",
                  "systemanalys", "lastenheft", "pflichtenheft"],
        },
        "kompetenzen": [],
    },
    "3": {
        "name": "Projektleitung / PMO",
        "zeichen": "③",
        "farbe": "#3B82F6",
        "stichworte": {
            "3": ["projektleit", "projektmanag", "pmo", "programmmanag", "programm-manag",
                  "projektsteuer"],
            "2": ["projektkoordinat", "projektreferent", "multiprojekt", "projektbüro",
                  "projektträger", "projektcontrolling", "geschäftsstellenleit"],
            "1": ["stabsstelle", "programmkoordinat"],
        },
        "kompetenzen": [],
    },
    "4": {
        "name": "Prozess- & Changemanagement",
        "zeichen": "④",
        "farbe": "#06B6D4",
        "stichworte": {
            "3": ["prozessmanag", "prozessoptimier", "organisationsentwickl",
                  "changemanag", "change manag", "change-manag", "veränderungsmanag"],
            "2": ["prozessberat", "geschäftsprozess", "organisationsberat", "organisationsmanag",
                  "qualitätsmanag", "wissensmanag", "prozessanalys", "prozessgestaltung",
                  "aufbauorganisation", "ablauforganisation"],
            "1": ["organisationsreferent", "innere dienste", "zentrale steuerung",
                  "verwaltungsorganisation", "geschäftsprozessmodellier"],
        },
        "kompetenzen": [],
    },
    "5": {
        "name": "Kunden- & Servicemanagement",
        "zeichen": "⑤",
        "farbe": "#10B981",
        "stichworte": {
            "3": ["kundenmanag", "key account", "key-account", "account manag", "accountmanag",
                  "servicemanag", "service manag", "service-manag", "service owner"],
            "2": ["kundenbetreu", "kundenberat", "servicekatalog", "partnermanag",
                  "beziehungsmanag", "crm-manag", "kundenbeziehung", "servicedesk-leit",
                  "kundenservice-leit", "stakeholdermanag"],
            "1": ["vertriebsreferent", "beratung und betreuung", "ansprechperson für kunden"],
        },
        "kompetenzen": [],
    },
    "6": {
        "name": "Wissenschafts- & Fördermanagement",
        "zeichen": "⑥",
        "farbe": "#F59E0B",
        "stichworte": {
            "3": ["wissenschaftsmanag", "drittmittelmanag", "fördermittelmanag",
                  "forschungsförder", "förderprogramm", "transfermanag"],
            "2": ["drittmittel", "fördermittel", "forschungsreferent", "wissenstransfer",
                  "wirtschaftsförder", "hochschulverwalt", "fakultätsgeschäftsführ",
                  "clustermanag", "förderberat", "eu-förder", "zuwendung"],
            "1": ["referent für forschung", "technologietransfer", "innovationsmanag",
                  "netzwerkmanag"],
        },
        "kompetenzen": [],
    },
}


# ----------------------------------------------------------------------------------
# 2 · GEWICHTUNG
#
# Hier entscheidet sich, was eine Stelle „wert" ist. Wer gerade auf kurze Wege
# aus ist, dreht die Regionen hoch; wer aufs Entgelt schaut, die Entgeltgruppen.
# ----------------------------------------------------------------------------------

STANDARD_GEWICHTE = {
    "berufsfeld_hoechstens": 9,
    "mehrere_felder": 2,
    "unbefristet": 3,
    "befristet": -1,
    "leitungsfunktion": 2,
    "frist_vorhanden": 1,
    "regionen": {
        "Potsdam": 5, "Babelsberg": 5, "Potsdam-Mittelmark": 4, "Werder": 3,
        "Teltow": 3, "Kleinmachnow": 3, "Stahnsdorf": 3, "Berlin": 4,
        "Brandenburg": 2, "Bundesweit": 0, "Sonstige": 1,
    },
    "sektoren": {
        "oed_bb": 4, "oed_be": 3, "oed_bund": 3,
        "wissenschaft": 2, "beratung": 3, "privat": 1,
    },
    "entgelt": {
        "E 9": -2, "E 10": 0, "E 11": 3, "E 12": 4, "E 13": 4, "E 14": 3, "E 15": 1,
        "A 10": -2, "A 11": 0, "A 12": 2, "A 13": 3, "A 14": 3, "A 15": 1,
    },
}

# Erklärtexte für die Oberfläche — damit klar ist, was ein Regler bewirkt.
GEWICHT_ERKLAERUNG = {
    "berufsfeld_hoechstens": "Obergrenze für die Punkte aus den Berufsfeld-Stichworten. "
                             "Höher = das Fachliche zählt mehr als alles andere.",
    "mehrere_felder": "Zuschlag, wenn eine Stelle auf mehrere Berufsfelder passt.",
    "unbefristet": "Zuschlag für eine unbefristete Stelle.",
    "befristet": "Abzug für eine befristete Stelle (negative Zahl eingeben).",
    "leitungsfunktion": "Zuschlag, wenn der Titel nach Leitung oder Stabsstelle klingt.",
    "frist_vorhanden": "Kleiner Zuschlag, wenn eine Bewerbungsfrist angegeben ist.",
}


# ----------------------------------------------------------------------------------
# 3 · PROFIL
# ----------------------------------------------------------------------------------

STANDARD_PROFIL = {
    # Beispielprofil. Es dient nur dazu, dass das Programm beim ersten Start
    # etwas anzuzeigen hat. Das eigene Profil wird im Fenster unter
    # „Berufsfelder" eingetragen und landet in profil.json — nicht hier.
    "name": "Mein Name",
    "abschluss": "Mein Abschluss",
    "wohnort": "Mein Wohnort",
    "verfuegbar": "ab sofort",
    "werdegang": [
        "20XX–heute · Stelle, Arbeitgeber, Ort",
        "20XX–20XX · frühere Stelle, Arbeitgeber, Ort",
        "Studium Fachrichtung, Hochschule (Abschluss)",
    ],
    "staerken": [
        "Was für die gesuchten Stellen übergreifend zählt — Berufsjahre, "
        "Branchenwechsel, Verfügbarkeit.",
        "Ein Satz je Stärke. Das KI-Briefing der Favoriten greift darauf zurück.",
    ],
    "weiterbildungen": [],
}


# ----------------------------------------------------------------------------------
# LADEN UND SPEICHERN
# ----------------------------------------------------------------------------------

def _laden(pfad, standard):
    """Liest eine JSON-Datei. Fehlt sie oder ist sie kaputt, gilt der Standard."""
    if not os.path.exists(pfad):
        return copy.deepcopy(standard)
    try:
        with open(pfad, encoding="utf-8") as datei:
            daten = json.load(datei)
    except (OSError, ValueError):
        return copy.deepcopy(standard)
    if not isinstance(daten, dict) or not daten:
        return copy.deepcopy(standard)
    return daten


def _speichern(pfad, daten):
    with open(pfad, "w", encoding="utf-8") as datei:
        json.dump(daten, datei, ensure_ascii=False, indent=2)


def felder_laden():
    daten = _laden(FELDER_DATEI, STANDARD_FELDER)
    # Fehlende Teile aus dem Standard auffüllen, damit eine von Hand gekürzte
    # Datei das Programm nicht lahmlegt.
    for nummer, vorgabe in STANDARD_FELDER.items():
        eintrag = daten.setdefault(nummer, copy.deepcopy(vorgabe))
        for schluessel, wert in vorgabe.items():
            eintrag.setdefault(schluessel, copy.deepcopy(wert))
        for stufe in ("1", "2", "3"):
            eintrag["stichworte"].setdefault(stufe, [])
    return daten


def felder_speichern(daten):
    _speichern(FELDER_DATEI, daten)


def gewichte_laden():
    daten = _laden(GEWICHTE_DATEI, STANDARD_GEWICHTE)
    for schluessel, wert in STANDARD_GEWICHTE.items():
        if isinstance(wert, dict):
            unter = daten.setdefault(schluessel, {})
            for k, v in wert.items():
                unter.setdefault(k, v)
        else:
            daten.setdefault(schluessel, wert)
    return daten


def gewichte_speichern(daten):
    _speichern(GEWICHTE_DATEI, daten)


def profil_laden():
    daten = _laden(PROFIL_DATEI, STANDARD_PROFIL)
    for schluessel, wert in STANDARD_PROFIL.items():
        daten.setdefault(schluessel, copy.deepcopy(wert))
    return daten


def profil_speichern(daten):
    _speichern(PROFIL_DATEI, daten)


def zuruecksetzen(bereich):
    """Stellt den Auslieferungszustand eines Bereichs wieder her."""
    pfad = {"felder": FELDER_DATEI, "gewichte": GEWICHTE_DATEI,
            "profil": PROFIL_DATEI}[bereich]
    if os.path.exists(pfad):
        os.remove(pfad)


def ist_geaendert(bereich):
    pfad = {"felder": FELDER_DATEI, "gewichte": GEWICHTE_DATEI,
            "profil": PROFIL_DATEI}[bereich]
    return os.path.exists(pfad)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    felder = felder_laden()
    print(f"{len(felder)} Berufsfelder "
          f"({'eigene Fassung' if ist_geaendert('felder') else 'Auslieferungszustand'})")
    for nummer, feld in sorted(felder.items()):
        anzahl = sum(len(w) for w in feld["stichworte"].values())
        print(f"  {feld['zeichen']} {feld['name']:42} {anzahl:3} Stichworte, "
              f"{len(feld['kompetenzen'])} Kompetenzen")
    gewichte = gewichte_laden()
    print(f"\nGewichtung "
          f"({'eigene Fassung' if ist_geaendert('gewichte') else 'Auslieferungszustand'}):")
    print(f"  Regionen: {gewichte['regionen']}")
    print(f"  Sektoren: {gewichte['sektoren']}")
