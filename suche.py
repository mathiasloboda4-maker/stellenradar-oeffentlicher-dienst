# -*- coding: utf-8 -*-
"""Suchsteuerung: führt die Quellen zusammen, ordnet ein, speichert.

Ablauf eines Laufs:

  1. INTERAMT — Umkreissuche um Potsdam. Liefert Berlin, Potsdam und Umgebung
     mit Frist, Entgelt und Entfernung schon in der Liste.
  2. Die 93 Arbeitgeberseiten des Registers.
  3. Je Kandidat: Vorfilter über den Titel, dann Detailseite holen, einordnen,
     speichern. Bereits verworfene Stellen werden nicht erneut geladen.

Zwei Betriebsarten, weil die Gründlichkeit richtig Zeit kostet:

  schnell (Standard)  Nur Kandidaten, deren TITEL ein Berufsfeld trifft, werden
                      im Detail geladen. Schnell, verpasst aber Stellen mit
                      nichtssagendem Titel („Sachbearbeitung im Referat 23").
  gründlich           Jede nicht hart ausgeschlossene Stelle wird geladen und
                      am Volltext geprüft. Findet mehr, dauert deutlich länger.
"""

import time
import traceback
from datetime import date

import arbeitgeber as agm
import datenbank as db
import einordnung as eo
import holen
import quelle_berlin as berlin
import quelle_interamt as interamt


class Abbruch(Exception):
    """Wird geworfen, wenn der Nutzer den Lauf stoppt."""


class Lauf:
    """Ein Suchlauf. Kapselt Fortschritt, Abbruch und Protokoll."""

    def __init__(self, melden=None, fortschritt=None, gruendlich=False,
                 interamt_runden=25, max_km=70, nur_gruppen=None,
                 mit_archiv=True, berlin_seiten=32):
        self.melden = melden or (lambda text: None)
        self.fortschritt = fortschritt or (lambda getan, gesamt: None)
        self.gruendlich = gruendlich
        self.interamt_runden = interamt_runden
        self.max_km = max_km
        self.nur_gruppen = set(nur_gruppen) if nur_gruppen else None
        self.mit_archiv = mit_archiv
        self.berlin_seiten = berlin_seiten
        self.archiviert = 0
        self.abbrechen = False
        self.gesehen = 0
        self.neu = 0
        self.aktualisiert = 0
        self.verworfen = 0
        self.fehler = []

    # -- Hilfen ---------------------------------------------------------------
    def _pruefe_abbruch(self):
        if self.abbrechen:
            raise Abbruch()

    def _sagen(self, text):
        self.melden(text)

    # -- Einzelne Stelle ------------------------------------------------------
    def _verarbeiten(self, kandidat, ag_eintrag, quelle, vorab=None):
        """Nimmt einen Kandidaten, prüft, lädt bei Bedarf den Volltext,
        ordnet ein und speichert. Gibt zurück, was passiert ist."""
        self._pruefe_abbruch()
        titel = eo.aufraeumen(kandidat["titel"])
        url = kandidat["url"]
        self.gesehen += 1

        # 1. Harter Ausschluss am Titel — billigster Filter, zuerst
        grund = eo.ist_ausgeschlossen(titel)
        if grund:
            self.verworfen += 1
            return "ausgeschlossen"

        # 2. Schon bekannt? Verworfene nie wieder anfassen.
        bekannt, status = db.kennt_url(url)
        if bekannt and status == db.VERWORFEN:
            return "bereits verworfen"

        # 3. Vorfilter im schnellen Modus: Titel muss ein Feld treffen
        titel_felder = eo.felder_bestimmen(titel)
        if not titel_felder and not self.gruendlich:
            self.verworfen += 1
            return "Titel ohne Berufsfeld (schneller Modus)"

        # 4. Volltext holen. Bei Stellen, die nur in einer Liste stehen, gibt es
        #    keine eigene Detailseite — dann bleibt der Titel die Grundlage.
        volltext = ""
        if not kandidat.get("aus_liste"):
            try:
                if quelle == "Interamt":
                    volltext = interamt.volltext_holen(url)
                elif quelle == "Karriereportal Berlin":
                    volltext = berlin.volltext_holen(url)
                else:
                    volltext = holen.volltext_holen(
                        url, tief=bool(ag_eintrag and ag_eintrag.get("tief")))
            except Exception as fehler:
                self.fehler.append(f"{titel[:40]}: {type(fehler).__name__}")
                volltext = ""

        # Das Berliner Portal nennt die ausschreibende Behörde nicht in der
        # Übersicht, wohl aber im Detailtext. Ohne das stünde bei allen 600
        # Stellen nur „Land Berlin".
        if quelle == "Karriereportal Berlin" and volltext and vorab is not None:
            vorab = dict(vorab)
            vorab["arbeitgeber"] = berlin.arbeitgeber_finden(volltext)

        # 5. Einordnen
        daten, ablehnung = eo.einordnen(
            titel, volltext, url,
            arbeitgeber=ag_eintrag or {
                "name": (vorab or {}).get("arbeitgeber"),
                "sektor": (vorab or {}).get("sektor"),
                "region": (vorab or {}).get("region"),
                "ort": (vorab or {}).get("ort"),
            })
        if ablehnung:
            self.verworfen += 1
            return ablehnung

        # 6. Angaben aus der Trefferliste haben Vorrang, wo sie vorhanden sind:
        #    Interamt liefert Frist, Entgelt und Entfernung verlässlicher als
        #    jede Textsuche im Volltext.
        for schluessel in ("frist", "entgelt", "entfernung_km", "ort", "region",
                           "sektor", "arbeitgeber"):
            if vorab and vorab.get(schluessel):
                daten[schluessel] = vorab[schluessel]
        daten["quelle"] = quelle
        # Punkte neu rechnen, falls die Vorab-Angaben besser sind
        daten["punkte"], daten["punkte_gruende"] = eo.punkte_berechnen(daten)

        _, ist_neu = db.speichern(daten)
        if ist_neu:
            self.neu += 1
            frist = daten.get("frist") or "ohne Frist"
            self._sagen(f"  ＋ {daten['punkte']:2} P · {frist} · "
                        f"{(daten.get('arbeitgeber') or '')[:24]} · {titel[:52]}")
            return "neu"
        self.aktualisiert += 1
        return "aktualisiert"

    # -- Quelle 1: Interamt ---------------------------------------------------
    def interamt_durchsuchen(self):
        self._sagen("── Interamt (Umkreissuche Potsdam) ──")
        try:
            zeilen = interamt.trefferliste_holen(
                nachladen=self.interamt_runden, max_km=self.max_km,
                melden=self._sagen)
        except Exception as fehler:
            self.fehler.append(f"Interamt: {type(fehler).__name__}: {fehler}")
            self._sagen(f"  Interamt nicht erreichbar: {type(fehler).__name__}")
            return
        self._sagen(f"  {len(zeilen)} Stellen in der Liste, prüfe Eignung …")
        for nummer, zeile in enumerate(zeilen, 1):
            self._pruefe_abbruch()
            self.fortschritt(nummer, len(zeilen))
            self._verarbeiten({"titel": zeile["titel"], "url": zeile["url"]},
                              ag_eintrag=None, quelle="Interamt", vorab=zeile)

    # -- Quelle 2: Karriereportal Berlin -------------------------------------
    def berlin_durchsuchen(self):
        """Das Landesportal Berlin blättert über die Adresse und braucht keinen
        Browser. Als eine von 93 Arbeitgeberseiten behandelt lieferte es genau
        einen Treffer — bei über 600 ausgeschriebenen Stellen."""
        self._sagen("── Karriereportal Berlin ──")
        try:
            zeilen = berlin.trefferliste_holen(seiten=self.berlin_seiten,
                                               melden=self._sagen)
        except Exception as fehler:
            self.fehler.append(f"Karriereportal Berlin: {type(fehler).__name__}: {fehler}")
            self._sagen(f"  Karriereportal Berlin nicht erreichbar: {type(fehler).__name__}")
            return
        self._sagen(f"  {len(zeilen)} Stellen in der Liste, prüfe Eignung …")
        for nummer, zeile in enumerate(zeilen, 1):
            self._pruefe_abbruch()
            self.fortschritt(nummer, len(zeilen))
            self._verarbeiten({"titel": zeile["titel"], "url": zeile["url"]},
                              ag_eintrag=None, quelle="Karriereportal Berlin",
                              vorab=zeile)

    # -- Quelle 3: Arbeitgeberseiten -----------------------------------------
    def arbeitgeber_durchsuchen(self):
        liste = [e for e in agm.ARBEITGEBER
                 if not self.nur_gruppen or e["gruppe"] in self.nur_gruppen]
        self._sagen(f"── {len(liste)} Arbeitgeberseiten ──")
        for nummer, eintrag in enumerate(liste, 1):
            self._pruefe_abbruch()
            self.fortschritt(nummer, len(liste))
            self._sagen(f"[{nummer}/{len(liste)}] {eintrag['name']}")
            try:
                treffer, _weg, hinweis = holen.arbeitgeber_durchsuchen(eintrag)
            except Abbruch:
                raise
            except Exception as fehler:
                self.fehler.append(f"{eintrag['name']}: {type(fehler).__name__}")
                self._sagen(f"      Fehler: {type(fehler).__name__}")
                continue
            if hinweis:
                continue
            for kandidat in treffer:
                self._verarbeiten(kandidat, ag_eintrag=eintrag,
                                  quelle=eintrag["name"])

    # -- Ausschreibungsseiten sichern ----------------------------------------
    def _archivieren(self):
        import archiv
        offen = [z["id"] for z in db.ohne_archiv()]
        if not offen:
            return
        self._sagen(f"── Sichere {len(offen)} Ausschreibungsseiten als PDF ──")
        for nummer, kennung in enumerate(offen, 1):
            self._pruefe_abbruch()
            self.fortschritt(nummer, len(offen))
            zeile = db.eine(kennung)
            if not zeile:
                continue
            try:
                archiv.stelle_archivieren(kennung)
                self.archiviert += 1
            except Exception as fehler:
                self.fehler.append(f"Archiv {zeile['titel'][:36]}: {fehler}")
        self._sagen(f"{self.archiviert} von {len(offen)} Seiten gesichert.")

    # -- Gesamtlauf -----------------------------------------------------------
    def starten(self, mit_interamt=True, mit_arbeitgebern=True, mit_berlin=True):
        db.einrichten()
        lauf_id = db.lauf_beginnen()
        begonnen = time.time()
        abgebrochen = False
        try:
            if mit_interamt:
                self.interamt_durchsuchen()
            if mit_berlin:
                self.berlin_durchsuchen()
            if mit_arbeitgebern:
                self.arbeitgeber_durchsuchen()
        except Abbruch:
            abgebrochen = True
            self._sagen("Lauf abgebrochen. Bisherige Treffer sind gespeichert.")
        except Exception:
            self.fehler.append(traceback.format_exc()[-1500:])
            self._sagen("Unerwarteter Fehler — Einzelheiten im Protokoll.")

        # Ausschreibungsseiten sichern. Das passiert NACH der Suche, damit die
        # Suche selbst schnell bleibt — und weil es der eigentliche Zweck ist:
        # Portale nehmen Ausschreibungen nach Fristende offline, oft ohne
        # Vorwarnung. Danach ist ohne Kopie nicht mehr nachvollziehbar, worauf
        # man sich beworben hat.
        if self.mit_archiv and not abgebrochen:
            try:
                self._archivieren()
            except Abbruch:
                self._sagen("Archivierung abgebrochen.")
            except Exception as fehler:
                self.fehler.append(f"Archiv: {type(fehler).__name__}: {fehler}")

        quellen = (1 if mit_interamt else 0) + (len(agm.ARBEITGEBER)
                                                if mit_arbeitgebern else 0)
        db.lauf_beenden(lauf_id, quellen, self.gesehen, self.neu, self.verworfen,
                        "\n".join(self.fehler) if self.fehler else None)
        dauer = time.time() - begonnen
        self._sagen("")
        self._sagen(f"{'Abgebrochen' if abgebrochen else 'Fertig'} nach "
                    f"{dauer / 60:.1f} Minuten: {self.gesehen} geprüft, "
                    f"{self.neu} neu, {self.aktualisiert} aufgefrischt, "
                    f"{self.verworfen} nicht passend, "
                    f"{self.archiviert} Seiten archiviert, "
                    f"{len(self.fehler)} Fehler.")
        return {"gesehen": self.gesehen, "neu": self.neu,
                "aktualisiert": self.aktualisiert, "verworfen": self.verworfen,
                "archiviert": self.archiviert,
                "fehler": self.fehler, "dauer": dauer,
                "abgebrochen": abgebrochen}


def nachfiltern(melden=None):
    """Prüft die gespeicherten Stellen noch einmal gegen die aktuellen Regeln.

    Wer die Stichwortlisten in `einordnung.py` nachschärft, will nicht, dass
    die alten Fehltreffer stehen bleiben. Angefasst werden ausschließlich
    Stellen im Status „neu" — was schon vorgemerkt, beworben oder bewusst
    verworfen wurde, ist die Arbeit des Menschen und bleibt unangetastet.
    """
    def sagen(text):
        if melden:
            melden(text)

    db.einrichten()
    geprueft = aussortiert = neu_bewertet = 0
    for zeile in db.holen(status=db.NEU, sortierung="punkte"):
        geprueft += 1
        grundlage = zeile["titel"] + "\n" + (zeile["volltext"] or "")
        grund = eo.ist_ausgeschlossen(zeile["titel"])
        if not grund and not eo.felder_bestimmen(grundlage):
            grund = "kein Berufsfeld mehr erkannt"
        if grund:
            db.status_setzen([zeile["id"]], db.VERWORFEN)
            aussortiert += 1
            sagen(f"  − {zeile['titel'][:58]}  ({grund})")
            continue
        # Punkte mit den aktuellen Regeln neu rechnen
        daten = dict(zeile)
        daten["feld_punkte"] = 0
        titel_treffer = eo.felder_bestimmen(zeile["titel"])
        if titel_treffer:
            daten["feld_punkte"] = titel_treffer[0][1] + 2
        punkte, gruende = eo.punkte_berechnen(daten)
        if punkte != zeile["punkte"]:
            with db.verbinden() as v:
                v.execute("UPDATE stellen SET punkte=?, punkte_gruende=? WHERE id=?",
                          (punkte, " | ".join(gruende), zeile["id"]))
            neu_bewertet += 1
    sagen(f"{geprueft} geprüft, {aussortiert} nachträglich aussortiert, "
          f"{neu_bewertet} neu bewertet.")
    return {"geprueft": geprueft, "aussortiert": aussortiert,
            "neu_bewertet": neu_bewertet}


def eckdaten_neu(melden=None):
    """Zieht Frist, Entgelt, Kontakt und die übrigen Eckdaten noch einmal aus
    den gespeicherten Ausschreibungstexten.

    Nötig, wenn die Erkennung verbessert wurde — sonst profitieren nur neu
    gefundene Stellen davon. Angaben, die aus einer Trefferliste stammen
    (Interamt liefert Frist und Entgelt mit), werden nicht überschrieben,
    wenn im Text nichts Besseres steht.
    """
    def sagen(text):
        if melden:
            melden(text)

    db.einrichten()
    eo.neu_laden()
    zeilen = db.holen(status=[db.NEU, db.VORGEMERKT, db.BEWORBEN])
    geaendert = 0
    with db.verbinden() as v:
        for zeile in zeilen:
            volltext = zeile["volltext"] or ""
            if not volltext:
                continue
            neu_werte = {
                "frist": eo.frist_finden(volltext) or zeile["frist"],
                "eintritt": eo.eintritt_finden(volltext) or zeile["eintritt"],
                "entgelt": eo.entgelt_finden(zeile["titel"] + chr(10) + volltext)
                           or zeile["entgelt"],
                "umfang": eo.umfang_finden(volltext) or zeile["umfang"],
                "befristung": eo.befristung_finden(volltext) or zeile["befristung"],
                "kontakt": eo.kontakt_finden(volltext) or zeile["kontakt"],
                "telefon": eo.telefon_finden(volltext) or zeile["telefon"],
                "email": eo.email_finden(volltext) or zeile["email"],
            }
            abweichend = {k: w for k, w in neu_werte.items() if w != zeile[k]}
            if not abweichend:
                continue
            v.execute(
                "UPDATE stellen SET " +
                ", ".join(f"{k}=?" for k in abweichend) + " WHERE id=?",
                list(abweichend.values()) + [zeile["id"]])
            geaendert += 1
            sagen(f"  ~ {zeile['titel'][:48]}: "
                  + ", ".join(f"{k}={w}" for k, w in abweichend.items()))
    sagen(f"{len(zeilen)} Stellen geprüft, {geaendert} aufgefrischt.")
    return {"geprueft": len(zeilen), "geaendert": geaendert}


def punkte_neu(melden=None):
    """Rechnet die Punkte aller Stellen mit der aktuellen Gewichtung neu.

    Wird aufgerufen, nachdem jemand in der Gewichtung etwas verstellt hat —
    etwa die Nähe hochgedreht. Ohne das würden die alten Werte stehen bleiben
    und die Sortierung wäre nicht mehr die, die man eingestellt hat."""
    def sagen(text):
        if melden:
            melden(text)

    db.einrichten()
    eo.neu_laden()
    gewichte = eo.GEWICHTE
    zeilen = db.holen(status=[db.NEU, db.VORGEMERKT, db.BEWORBEN, db.VERWORFEN])
    geaendert = 0
    with db.verbinden() as v:
        for zeile in zeilen:
            daten = dict(zeile)
            titel_treffer = eo.felder_bestimmen(zeile["titel"])
            daten["feld_punkte"] = (titel_treffer[0][1] + 2) if titel_treffer else 0
            punkte, gruende = eo.punkte_berechnen(daten, gewichte)
            if punkte != zeile["punkte"]:
                v.execute("UPDATE stellen SET punkte=?, punkte_gruende=? WHERE id=?",
                          (punkte, " | ".join(gruende), zeile["id"]))
                geaendert += 1
    sagen(f"{len(zeilen)} Stellen geprüft, {geaendert} neu bewertet.")
    return {"geprueft": len(zeilen), "geaendert": geaendert}


def schnelllauf(**kwargs):
    """Bequemer Einstieg für die Befehlszeile."""
    return Lauf(melden=lambda t: print(t), **kwargs).starten()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    if "--eckdaten-neu" in sys.argv:
        eckdaten_neu(melden=print)
        punkte_neu(melden=print)
        sys.exit(0)
    if "--punkte-neu" in sys.argv:
        punkte_neu(melden=print)
        sys.exit(0)
    if "--nachfiltern" in sys.argv:
        nachfiltern(melden=print)
        sys.exit(0)
    gruendlich = "--gruendlich" in sys.argv
    runden = 25
    if "--runden" in sys.argv:
        runden = int(sys.argv[sys.argv.index("--runden") + 1])
    nur_interamt = "--nur-interamt" in sys.argv
    nur_seiten = "--nur-seiten" in sys.argv
    lauf = Lauf(melden=print, gruendlich=gruendlich, interamt_runden=runden)
    lauf.starten(mit_interamt=not nur_seiten, mit_arbeitgebern=not nur_interamt)
