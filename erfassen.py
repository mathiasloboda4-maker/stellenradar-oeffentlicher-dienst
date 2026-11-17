# -*- coding: utf-8 -*-
"""Eine Stelle von Hand erfassen.

Nicht alles kommt über die Portale. Ein Hinweis aus dem Bekanntenkreis, ein
Fund auf LinkedIn, eine Ausschreibung, die jemand per Mail schickt — ohne
diesen Weg lebt so eine Stelle außerhalb des Programms: kein Briefing, keine
Seitenkopie, keine Frist im Dashboard.

Zwei Wege, beide enden im selben Datensatz wie ein gefundener Treffer:

  aus_link(url)      Seite abrufen, Text ziehen, einordnen — der Normalfall
  aus_text(titel, text)  wenn die Seite sich nicht abrufen lässt, etwa weil
                         sie eine Anmeldung verlangt: Text von Hand einfügen

Die Stelle bekommt `manuell = 1` und die Quelle „von Hand". Sie wird von einem
späteren Suchlauf nicht überschrieben und nicht aussortiert — bei einer selbst
eingetragenen Stelle hat der Mensch entschieden, nicht der Stichwortfilter.
"""

import re
from datetime import date

import datenbank as db
import einordnung as eo
import holen

QUELLE = "von Hand"


class ErfassungsFehler(RuntimeError):
    pass


def url_normieren(eingabe):
    u = (eingabe or "").strip().strip('<>"„“')
    if not u:
        return ""
    if u.startswith("www."):
        u = "https://" + u
    if not re.match(r"^https?://", u, re.IGNORECASE):
        if "." not in u.split("/")[0]:
            return ""
        u = "https://" + u
    return u


def _speichern(titel, volltext, url, arbeitgeber=None, region=None, sektor=None,
               ort=None):
    eo.neu_laden()
    vorgabe = {"name": arbeitgeber, "sektor": sektor or "privat",
               "region": region or "Sonstige", "ort": ort}
    daten, ablehnung = eo.einordnen(titel, volltext, url, arbeitgeber=vorgabe)

    if ablehnung:
        # Von Hand erfasst heißt: Der Mensch will sie haben. Der Stichwortfilter
        # darf sie nicht wegwerfen — aber der Grund wird festgehalten.
        daten = {
            "titel": eo.aufraeumen(titel), "url": url,
            "arbeitgeber": arbeitgeber, "sektor": sektor or "privat",
            "region": region or "Sonstige", "ort": ort,
            "felder": [], "feld_haupt": None, "feld_punkte": 0,
            "frist": eo.frist_finden(volltext),
            "eintritt": eo.eintritt_finden(volltext),
            "entgelt": eo.entgelt_finden(titel + "\n" + volltext),
            "umfang": eo.umfang_finden(volltext),
            "befristung": eo.befristung_finden(volltext),
            "kontakt": eo.kontakt_finden(volltext),
            "telefon": eo.telefon_finden(volltext),
            "email": eo.email_finden(volltext),
            "volltext": volltext,
        }
        daten["punkte"], daten["punkte_gruende"] = eo.punkte_berechnen(daten)
        daten["notiz"] = f"Von Hand erfasst. Hinweis des Filters: {ablehnung}."

    if arbeitgeber:
        daten["arbeitgeber"] = arbeitgeber
    if ort:
        daten["ort"] = ort
    daten["quelle"] = QUELLE
    daten["manuell"] = 1
    daten.setdefault("gefunden_am", date.today().isoformat())

    kennung, ist_neu = db.speichern(daten)
    if not ist_neu:
        # War schon da — dann wenigstens als von Hand bestätigt markieren
        with db.verbinden() as v:
            v.execute("UPDATE stellen SET manuell=1 WHERE id=?", (kennung,))
    return kennung, ist_neu, (ablehnung or None)


def aus_link(url, arbeitgeber=None, region=None, sektor=None, melden=None):
    """Holt die Seite, zieht den Text und legt die Stelle an."""
    def sagen(was):
        if melden:
            melden(was)

    adresse = url_normieren(url)
    if not adresse:
        raise ErfassungsFehler(
            "Das sieht nicht nach einer Internetadresse aus. Bitte den "
            "vollständigen Link einfügen, zum Beispiel https://…")

    bekannt, status = db.kennt_url(adresse)
    if bekannt:
        sagen("Diese Stelle ist schon in der Liste.")

    sagen("Rufe die Seite ab …")
    try:
        volltext = holen.volltext_holen(adresse)
    except Exception as fehler:
        raise ErfassungsFehler(
            f"Die Seite konnte nicht gelesen werden ({type(fehler).__name__}).\n\n"
            f"Tipp: Die Ausschreibung im Browser öffnen, den Text markieren "
            f"(Strg+A), kopieren (Strg+C) und hier auf „Text einfügen…\" "
            f"klicken.") from fehler

    if len(volltext.split()) < 40:
        raise ErfassungsFehler(
            "Von dieser Seite ließ sich kaum Text gewinnen — womöglich verlangt "
            "sie eine Anmeldung oder lädt ihren Inhalt nach.\n\n"
            "Tipp: Text im Browser kopieren und über „Text einfügen…\" eintragen.")

    titel = _titel_raten(volltext) or adresse
    sagen(f"Gelesen: {len(volltext.split())} Wörter")
    return _speichern(titel, volltext, adresse, arbeitgeber, region, sektor)


def aus_text(titel, volltext, url=None, arbeitgeber=None, region=None,
             sektor=None, ort=None):
    """Für Seiten, die sich nicht abrufen lassen: Text von Hand einfügen."""
    titel = eo.aufraeumen(titel)
    if not titel or len(titel) < 6:
        raise ErfassungsFehler("Bitte eine Stellenbezeichnung eintragen.")
    if len((volltext or "").split()) < 40:
        raise ErfassungsFehler(
            f"Der Text ist sehr kurz ({len((volltext or '').split())} Wörter). "
            f"Für Briefing und Einordnung braucht es die ganze Ausschreibung.")
    adresse = url_normieren(url) if url else ""
    if not adresse:
        # Ohne Adresse braucht der Datensatz trotzdem einen eindeutigen Schlüssel
        kennung = re.sub(r"[^\w]+", "-", titel.lower())[:60].strip("-")
        adresse = f"vonhand://{date.today().isoformat()}/{kennung}"
    return _speichern(titel, volltext, adresse, arbeitgeber, region, sektor, ort)


# Die erste Zeile mit Geschlechtskürzel ist fast immer die Stellenbezeichnung.
def _titel_raten(text):
    for zeile in (text or "").splitlines():
        zeile = eo.aufraeumen(zeile)
        if 12 <= len(zeile) <= 190 and eo.GESCHLECHT_RE.search(zeile):
            if not eo.ist_menuetext(zeile):
                return zeile
    for zeile in (text or "").splitlines():
        zeile = eo.aufraeumen(zeile)
        if 14 <= len(zeile) <= 120 and not eo.ist_menuetext(zeile):
            return zeile
    return None


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    db.einrichten()
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    kennung, ist_neu, hinweis = aus_link(sys.argv[1], melden=lambda w: print(" ·", w))
    zeile = db.eine(kennung)
    print(f"\n{'Neu angelegt' if ist_neu else 'Aktualisiert'}: {zeile['titel']}")
    print(f"  Arbeitgeber {zeile['arbeitgeber']}   Frist {zeile['frist']}   "
          f"Punkte {zeile['punkte']}")
    if hinweis:
        print(f"  Hinweis des Filters: {hinweis}")
