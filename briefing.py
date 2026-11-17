# -*- coding: utf-8 -*-
"""Vorbereitungs-Briefing zu einer favorisierten Stelle.

Zweck: In wenigen Minuten wissen, worauf man sich bei dieser Stelle einlässt —
für das Anschreiben und für ein Vorstellungsgespräch.

Aufbau, und warum er so ist:

  ① KEY FACTS ZUR STELLE      aus der Datenbank, NICHT von der KI
  ② ANSPRECHPARTNER           aus der Datenbank, NICHT von der KI
  ③ WAS DIE STELLE VERLANGT   KI, streng am Ausschreibungstext
  ④ WO MEINE KOMPETENZEN PASSEN  KI, mit den hinterlegten Kompetenzen
  ⑤ DER ELEFANT IM RAUM       KI: Lücken benennen und drehen
  ⑥ ZUM ARBEITGEBER           KI aus ihrem Allgemeinwissen — ausdrücklich als
                              ungeprüft gekennzeichnet
  ⑦ FRAGEN FÜRS GESPRÄCH      KI

Alles Prüfbare steht in ① und ②. Die wurden deterministisch aus der
Ausschreibung gezogen und sind deshalb verlässlich. Was die KI beisteuert,
steht darunter — und Abschnitt ⑥ trägt einen Warnhinweis, weil ein lokales
Modell über einen konkreten Arbeitgeber oft wenig und manchmal Falsches weiß.
"""

import json
import re
from datetime import date, datetime

import datenbank as db
import einordnung as eo
import konfiguration as kfg
import ki

# So viel Ausschreibungstext geht an die KI. Mehr bringt wenig und kostet Zeit.
TEXT_GRENZE = 7000

TRENNER = "─" * 68


# ----------------------------------------------------------------------------------
# TEIL 1: DIE GESICHERTEN ANGABEN
# ----------------------------------------------------------------------------------

def _datum(iso):
    if not iso:
        return None
    try:
        return date.fromisoformat(iso).strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return str(iso)


def key_facts(zeile):
    """Die harten Angaben aus der Ausschreibung. Ohne KI, deshalb verlässlich."""
    tage = db.tage_bis_frist(zeile["frist"])
    if tage is None:
        frist = "nicht angegeben"
    elif tage < 0:
        frist = f"{_datum(zeile['frist'])} — ABGELAUFEN"
    elif tage == 0:
        frist = f"{_datum(zeile['frist'])} — HEUTE"
    else:
        frist = f"{_datum(zeile['frist'])} — noch {tage} Tage"

    zeilen = [
        ("Arbeitgeber", zeile["arbeitgeber"]),
        ("Bereich", eo.SEKTOREN.get(zeile["sektor"], zeile["sektor"])),
        ("Dienstort", zeile["ort"]),
        ("Entfernung", f"{zeile['entfernung_km']} km von Potsdam"
         if zeile["entfernung_km"] is not None else None),
        ("Entgelt", zeile["entgelt"]),
        ("Umfang", zeile["umfang"]),
        ("Befristung", zeile["befristung"]),
        ("Eintritt", zeile["eintritt"]),
        ("Bewerbungsfrist", frist),
        ("Passungs-Punkte", f"{zeile['punkte']} — {zeile['punkte_gruende']}"
         if zeile["punkte_gruende"] else str(zeile["punkte"])),
        ("Quelle", zeile["quelle"]),
        ("Link", zeile["url"]),
    ]
    return [(k, str(w)) for k, w in zeilen if w]


def ansprechpartner(zeile):
    zeilen = [
        ("Name", zeile["kontakt"]),
        ("Telefon", zeile["telefon"]),
        ("E-Mail", zeile["email"]),
    ]
    gefunden = [(k, str(w)) for k, w in zeilen if w]
    if not gefunden:
        return [("Hinweis", "In der Ausschreibung ist keine Ansprechperson genannt. "
                            "Vor dem Anruf auf der Seite des Arbeitgebers nachsehen.")]
    return gefunden


def passende_kompetenzen(zeile):
    """Die hinterlegten Kompetenzen zu den erkannten Berufsfeldern."""
    try:
        nummern = json.loads(zeile["felder"] or "[]")
    except (ValueError, TypeError):
        nummern = []
    if not nummern and zeile["feld_haupt"]:
        nummern = [zeile["feld_haupt"]]
    ergebnis = []
    for nummer in nummern[:3]:
        name = eo.FELDER.get(nummer, "")
        for beleg in eo.FELD_KOMPETENZEN.get(nummer, []):
            ergebnis.append((name, beleg))
    return ergebnis


# ----------------------------------------------------------------------------------
# TEIL 2: DIE EINSCHÄTZUNG DER KI
# ----------------------------------------------------------------------------------

# Name und Abschluss stehen nicht im Code, sondern im eigenen Profil
# (profil.json, im Fenster unter „Berufsfelder" zu pflegen).
SYSTEMTEXT_VORLAGE = """Du bereitest eine bewerbende Person auf eine konkrete
Stelle vor. Sie heißt {name}, hat den Abschluss {abschluss} und sucht im
öffentlichen Dienst und in der Beratung für die öffentliche Hand.

Schreibe auf Deutsch, in knappen Stichpunkten, sachlich und ohne Werbesprache.
Keine Einleitung, keine Zusammenfassung am Ende, keine Anrede.

Halte dich strikt an diese Regeln:
1. Alles, was du über die STELLE sagst, muss im Ausschreibungstext stehen.
   Erfinde keine Aufgaben, keine Anforderungen, keine Zahlen.
2. Alles, was du über die BEWERBENDE PERSON sagst, muss in ihrem Profil
   stehen. Erfinde keine Erfahrungen, keine Jahre, keine Führungsrollen.
3. Nur im Abschnitt ZUM ARBEITGEBER darfst du Allgemeinwissen verwenden.
   Wenn du über diesen Arbeitgeber nichts Sicheres weißt, schreibe genau das.
4. Verwende die vorgegebenen Überschriften wörtlich und in dieser Reihenfolge."""

ANWEISUNG = """AUSSCHREIBUNG
Titel: {titel}
Arbeitgeber: {arbeitgeber}
Dienstort: {ort}

Text der Ausschreibung:
{text}

PROFIL DER BEWERBENDEN PERSON
{werdegang}

Ihre Stärken:
{staerken}

Kompetenzen in den Berufsfeldern, die zu dieser Stelle passen:
{kompetenzen}

{weiterbildungen}

AUFGABE
Schreibe genau diese vier Abschnitte, jeweils mit der Überschrift in
Großbuchstaben in einer eigenen Zeile, darunter Stichpunkte mit „- ":

WAS DIE STELLE VERLANGT
4 bis 6 Stichpunkte: die wichtigsten Aufgaben und Anforderungen aus dem Text.

WO MEINE KOMPETENZEN PASSEN
3 bis 5 Stichpunkte. Verbinde je einen Punkt der Ausschreibung mit einem
konkreten Beleg aus dem Profil. Form: „Anforderung → Beleg".

DER ELEFANT IM RAUM
2 bis 3 Stichpunkte: Wo könnte das Profil nicht zur Ausschreibung passen?
Benenne es offen und schreibe dazu, wie sich das im Gespräch drehen lässt.

ZUM ARBEITGEBER
3 bis 5 Stichpunkte aus deinem Allgemeinwissen: Was tut dieser Arbeitgeber,
wie ist er aufgestellt, was ist für ein Gespräch nützlich? Wenn du nichts
Belastbares weißt, schreibe nur: „Kein gesichertes Wissen zu diesem
Arbeitgeber."

FRAGEN FÜRS GESPRÄCH
3 bis 4 Fragen, die man im Gespräch stellen kann und die zeigen, dass die
Ausschreibung gelesen wurde."""


def _systemtext():
    """Setzt Name und Abschluss aus dem Profil in den Systemtext ein."""
    profil = kfg.profil_laden()
    return SYSTEMTEXT_VORLAGE.format(
        name=profil.get("name") or "die bewerbende Person",
        abschluss=profil.get("abschluss") or "(nicht angegeben)")


def _profil_text():
    profil = kfg.profil_laden()
    werdegang = "\n".join(f"- {z}" for z in profil.get("werdegang", []))
    staerken = "\n".join(f"- {z}" for z in profil.get("staerken", []))
    weiter = profil.get("weiterbildungen", [])
    if weiter:
        weiterbildungen = ("Weiterbildungen und Zertifikate:\n"
                           + "\n".join(f"- {z}" for z in weiter))
    else:
        weiterbildungen = ""
    return werdegang, staerken, weiterbildungen


def ki_teil(zeile, modell=None, melden=None):
    """Lässt die KI die vier Einschätzungs-Abschnitte schreiben."""
    werdegang, staerken, weiterbildungen = _profil_text()
    kompetenzen = passende_kompetenzen(zeile)
    kompetenztext = "\n".join(f"- [{feld}] {beleg}" for feld, beleg in kompetenzen)
    if not kompetenztext:
        kompetenztext = "- (keine hinterlegt)"

    text = (zeile["volltext"] or "").strip()
    if not text:
        raise ki.KiFehler("Zu dieser Stelle ist kein Ausschreibungstext "
                          "gespeichert. Ohne Text kann die KI nichts aufbereiten.")
    if len(text) > TEXT_GRENZE:
        text = text[:TEXT_GRENZE] + "\n[…gekürzt]"

    anweisung = ANWEISUNG.format(
        titel=zeile["titel"], arbeitgeber=zeile["arbeitgeber"] or "unbekannt",
        ort=zeile["ort"] or "nicht angegeben", text=text,
        werdegang=werdegang, staerken=staerken, kompetenzen=kompetenztext,
        weiterbildungen=weiterbildungen)
    return ki.fragen(_systemtext(), anweisung, modell=modell, melden=melden)


# ----------------------------------------------------------------------------------
# ZUSAMMENBAU
# ----------------------------------------------------------------------------------

# Die KI schreibt die Überschriften nicht immer sauber ab — im Versuch kam
# „ZUM ARBITGEBER" zurück. Deshalb werden sie erkannt und einheitlich gesetzt.
ABSCHNITTE = [
    (r"was\s+die\s+stelle\s+verlangt", "④ WAS DIE STELLE VERLANGT"),
    (r"wo\s+meine\s+kompetenzen\s+passen", "⑤ WO MEINE KOMPETENZEN PASSEN"),
    (r"der\s+elefant\s+im\s+raum", "⑥ DER ELEFANT IM RAUM"),
    (r"zum\s+arb\w*?geber", "⑦ ZUM ARBEITGEBER  (Modellwissen — bitte prüfen)"),
    # Auch Umschreibungen ohne Umlaute erkennen (ue/ae), die kommen vor
    (r"fragen\s+f(?:ü|ue|u)rs?\s+gespr(?:ä|ae|a)ch", "⑧ FRAGEN FÜRS GESPRÄCH"),
]


def abschnitte_formatieren(text):
    """Setzt die Überschriften der KI-Abschnitte einheitlich und nummeriert sie."""
    zeilen = []
    for zeile in (text or "").splitlines():
        knapp = zeile.strip().strip(":").strip()
        ersetzt = None
        if knapp and len(knapp) < 70:
            for muster, ueberschrift in ABSCHNITTE:
                if re.fullmatch(muster, knapp, re.IGNORECASE):
                    ersetzt = f"\n{ueberschrift}\n{TRENNER}"
                    break
        zeilen.append(ersetzt if ersetzt is not None else zeile)
    zusammen = "\n".join(zeilen)
    return re.sub(r"\n{3,}", "\n\n", zusammen).strip()


def _block(ueberschrift, zeilen):
    teile = [ueberschrift, TRENNER]
    breite = max((len(k) for k, _ in zeilen), default=0)
    for schluessel, wert in zeilen:
        teile.append(f"{schluessel:<{breite}}   {wert}")
    return "\n".join(teile)


def grundgeruest(zeile):
    """Die gesicherten Abschnitte ① und ② plus die hinterlegten Kompetenzen.
    Steht auch ohne KI zur Verfügung."""
    teile = [_block("① KEY FACTS ZUR STELLE", key_facts(zeile)), "",
             _block("② ANSPRECHPARTNER", ansprechpartner(zeile)), ""]
    kompetenzen = passende_kompetenzen(zeile)
    if kompetenzen:
        zeilen = ["③ MEINE HINTERLEGTEN KOMPETENZEN FÜR DIESES FELD", TRENNER]
        letztes_feld = None
        for feld, beleg in kompetenzen:
            if feld != letztes_feld:
                zeilen.append(f"\n{feld}")
                letztes_feld = feld
            zeilen.append(f"  - {beleg}")
        teile.append("\n".join(zeilen))
        teile.append("")
    return "\n".join(teile)


HINWEIS_ARBEITGEBER = (
    "\n" + TRENNER + "\n"
    "Die Abschnitte oberhalb von „WAS DIE STELLE VERLANGT\" stammen direkt aus\n"
    "der Ausschreibung und sind verlässlich. Alles darunter hat die lokale KI\n"
    "geschrieben. Besonders „ZUM ARBEITGEBER\" kommt aus ihrem Allgemeinwissen\n"
    "und kann veraltet oder falsch sein — vor dem Gespräch nachprüfen.")


def erzeugen(kennung, modell=None, melden=None, nur_grundgeruest=False):
    """Baut das Briefing und legt es in der Datenbank ab."""
    zeile = db.eine(kennung)
    if not zeile:
        raise ValueError(f"Stelle {kennung} gibt es nicht.")

    kopf = grundgeruest(zeile)
    if nur_grundgeruest:
        text = kopf + ("\n" + TRENNER + "\n"
                       "Ohne KI erstellt. Für die Einschätzung zur Stelle, zum\n"
                       "Arbeitgeber und für Gesprächsfragen auf „Mit KI aufbereiten\"\n"
                       "klicken — dafür muss Ollama laufen.")
        db.briefing_merken(kennung, text, "ohne KI")
        return text, "ohne KI"

    einschaetzung, benutztes_modell = ki_teil(zeile, modell=modell, melden=melden)
    text = kopf + abschnitte_formatieren(einschaetzung) + HINWEIS_ARBEITGEBER
    db.briefing_merken(kennung, text, benutztes_modell)
    return text, benutztes_modell


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    db.einrichten()
    eo.neu_laden()
    favoriten = db.favoriten()
    if not favoriten:
        # Zum Ausprobieren die bestbewertete Stelle nehmen
        favoriten = db.holen(sortierung="punkte")[:1]
    if not favoriten:
        print("Keine Stellen in der Datenbank.")
        sys.exit(0)
    zeile = favoriten[0]
    print(f"Briefing für: {zeile['titel']}\n")
    if "--ohne-ki" in sys.argv:
        print(grundgeruest(zeile))
    else:
        text, modell = erzeugen(zeile["id"], melden=lambda t: print(f"  · {t}"))
        print(f"\n[Modell: {modell}]\n")
        print(text)
