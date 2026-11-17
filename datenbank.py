# -*- coding: utf-8 -*-
"""Datenhaltung des Stellenradars (SQLite).

Der wichtigste Unterschied zum alten Crawler: Eine gelöschte Stelle ist nicht
weg, sondern bekommt den Status „verworfen". Sonst findet der nächste Lauf sie
wieder und man sortiert dieselbe Stelle jede Woche erneut aus.

Status (die Triage):
  neu         frisch gefunden, noch nicht angesehen
  vorgemerkt  interessant, kommt auf die Merkliste
  beworben    Bewerbung ist raus
  verworfen   nicht interessant — wird nie wieder vorgeschlagen
"""

import json
import os
import sqlite3
from datetime import date, datetime

BASIS = os.path.dirname(os.path.abspath(__file__))
DB_PFAD = os.environ.get("STELLENRADAR_DB", os.path.join(BASIS, "stellenradar.db"))
PDF_ORDNER = os.path.join(os.path.dirname(DB_PFAD), "steckbriefe")

NEU, VORGEMERKT, BEWORBEN, VERWORFEN = "neu", "vorgemerkt", "beworben", "verworfen"
STATUS_NAMEN = {
    NEU: "🆕 neu",
    VORGEMERKT: "⭐ vorgemerkt",
    BEWORBEN: "✉ beworben",
    VERWORFEN: "🗑 verworfen",
}
STATUS_REIHE = [NEU, VORGEMERKT, BEWORBEN, VERWORFEN]

SCHEMA = """
CREATE TABLE IF NOT EXISTS stellen (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    url           TEXT UNIQUE NOT NULL,
    titel         TEXT NOT NULL,
    arbeitgeber   TEXT,
    quelle        TEXT,
    sektor        TEXT,
    region        TEXT,
    ort           TEXT,
    entfernung_km INTEGER,
    felder        TEXT,          -- JSON-Liste der Berufsfeld-Nummern
    feld_haupt    INTEGER,
    punkte        INTEGER DEFAULT 0,
    punkte_gruende TEXT,
    frist         TEXT,          -- ISO-Datum
    eintritt      TEXT,
    entgelt       TEXT,
    umfang        TEXT,
    befristung    TEXT,
    kontakt       TEXT,
    telefon       TEXT,
    email         TEXT,
    volltext      TEXT,
    pdf_pfad      TEXT,          -- Steckbrief (aufbereitet)
    archiv_pdf    TEXT,          -- Kopie der Originalseite
    favorit       INTEGER DEFAULT 0,
    beworben_am   TEXT,          -- wann die Bewerbung raus ist
    rueckmeldung  TEXT,          -- Eingangsbestaetigung, Einladung, Absage …
    wiedervorlage TEXT,          -- erinnere mich an diesem Tag
    manuell       INTEGER DEFAULT 0,   -- von Hand erfasst statt gefunden
    briefing      TEXT,          -- von der KI aufbereitete Kurzinfo
    briefing_am   TEXT,
    briefing_modell TEXT,
    gefunden_am   TEXT,
    geprueft_am   TEXT,
    status        TEXT DEFAULT 'neu',
    notiz         TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_status ON stellen(status);
CREATE INDEX IF NOT EXISTS idx_frist  ON stellen(frist);
CREATE INDEX IF NOT EXISTS idx_punkte ON stellen(punkte);

CREATE TABLE IF NOT EXISTS laeufe (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    begonnen    TEXT,
    beendet     TEXT,
    quellen     INTEGER,
    gesehen     INTEGER,
    neu         INTEGER,
    verworfen   INTEGER,
    fehler      TEXT
);
"""


def verbinden():
    verbindung = sqlite3.connect(DB_PFAD, timeout=20)
    verbindung.row_factory = sqlite3.Row
    verbindung.execute("PRAGMA journal_mode=WAL")
    return verbindung


# Spalten, die nach der ersten Fassung dazugekommen sind. Eine bestehende
# Datenbank wird beim Start nachgezogen, statt sie neu anlegen zu müssen.
NACHGEREICHTE_SPALTEN = {
    "archiv_pdf": "TEXT",
    "favorit": "INTEGER DEFAULT 0",
    "briefing": "TEXT",
    "briefing_am": "TEXT",
    "briefing_modell": "TEXT",
    "beworben_am": "TEXT",
    "rueckmeldung": "TEXT",
    "wiedervorlage": "TEXT",
    "manuell": "INTEGER DEFAULT 0",
}


def einrichten():
    os.makedirs(os.path.dirname(DB_PFAD), exist_ok=True)
    os.makedirs(PDF_ORDNER, exist_ok=True)
    with verbinden() as v:
        v.executescript(SCHEMA)
        vorhanden = {z["name"] for z in v.execute("PRAGMA table_info(stellen)")}
        for spalte, art in NACHGEREICHTE_SPALTEN.items():
            if spalte not in vorhanden:
                v.execute(f"ALTER TABLE stellen ADD COLUMN {spalte} {art}")
        # Erst NACH der Migration — bei einer alten Datenbank gibt es die
        # Spalte vorher noch nicht, und CREATE INDEX wuerde scheitern.
        v.execute("CREATE INDEX IF NOT EXISTS idx_favorit ON stellen(favorit)")


# ----------------------------------------------------------------------------------
# SCHREIBEN
# ----------------------------------------------------------------------------------

FELDER_DB = ["url", "titel", "arbeitgeber", "quelle", "sektor", "region", "ort",
             "entfernung_km", "felder", "feld_haupt", "punkte", "punkte_gruende",
             "frist", "eintritt", "entgelt", "umfang", "befristung", "kontakt",
             "telefon", "email", "volltext", "pdf_pfad", "archiv_pdf", "gefunden_am",
             "geprueft_am", "status", "notiz", "manuell"]


def kennt_url(url):
    """Ist die Stelle schon bekannt? Gibt (bekannt, status) zurück.
    Wird vor dem Abruf der Detailseite gefragt — so wird eine verworfene Stelle
    nicht erneut heruntergeladen."""
    with verbinden() as v:
        zeile = v.execute("SELECT status FROM stellen WHERE url=?", (url,)).fetchone()
    return (True, zeile["status"]) if zeile else (False, None)


def speichern(daten):
    """Legt eine Stelle an oder frischt eine bestehende auf.

    Bei einer bekannten Stelle werden nur die Sachangaben aktualisiert — Status
    und Notiz bleiben, denn das ist die Arbeit des Menschen."""
    satz = dict(daten)
    if isinstance(satz.get("felder"), (list, tuple)):
        satz["felder"] = json.dumps(list(satz["felder"]))
    if isinstance(satz.get("punkte_gruende"), (list, tuple)):
        satz["punkte_gruende"] = " | ".join(satz["punkte_gruende"])
    satz.setdefault("gefunden_am", date.today().isoformat())
    satz["geprueft_am"] = date.today().isoformat()
    satz.setdefault("status", NEU)
    satz.setdefault("notiz", "")

    werte = {k: satz.get(k) for k in FELDER_DB}
    with verbinden() as v:
        vorhanden = v.execute("SELECT id FROM stellen WHERE url=?",
                              (werte["url"],)).fetchone()
        if vorhanden:
            # Status, Notiz, Fundtag und die bereits erzeugten PDFs nicht
            # überschreiben — die sind Arbeit, die nicht verloren gehen darf.
            zu_setzen = [k for k in FELDER_DB
                         if k not in ("url", "status", "notiz", "gefunden_am",
                                      "pdf_pfad", "archiv_pdf", "manuell")]
            v.execute(
                f"UPDATE stellen SET {', '.join(k + '=?' for k in zu_setzen)} "
                f"WHERE url=?",
                [werte[k] for k in zu_setzen] + [werte["url"]])
            return vorhanden["id"], False
        spalten = ", ".join(FELDER_DB)
        platz = ", ".join("?" for _ in FELDER_DB)
        zeiger = v.execute(f"INSERT INTO stellen ({spalten}) VALUES ({platz})",
                           [werte[k] for k in FELDER_DB])
        return zeiger.lastrowid, True


def status_setzen(kennungen, status):
    """Setzt den Status. Beim Verwerfen werden die Dokumente mit entfernt.

    Begründung: Zu jeder Stelle liegen ein Steckbrief und eine archivierte
    Seite. Was man aussortiert hat, braucht man nicht mehr — sonst wächst der
    Ordner mit Unterlagen zu Stellen voll, die nie infrage kamen. Holt man eine
    Stelle später zurück, steht sie ohne Dokumente da und lässt sich neu
    sichern; die Originalseite ist dann allerdings vielleicht schon offline.
    """
    kennungen = [int(k) for k in kennungen]
    entfernt = 0
    if status == VERWORFEN:
        entfernt = dokumente_loeschen(kennungen)
    with verbinden() as v:
        v.executemany("UPDATE stellen SET status=? WHERE id=?",
                      [(status, k) for k in kennungen])
        if status == VERWORFEN:
            # Auch das Briefing ist dann hinfällig
            v.executemany("UPDATE stellen SET favorit=0, briefing=NULL, "
                          "briefing_am=NULL WHERE id=?", [(k,) for k in kennungen])
    return entfernt


def dokumente_loeschen(kennungen):
    """Löscht Steckbrief und archivierte Seite zu den genannten Stellen."""
    entfernt = 0
    with verbinden() as v:
        for kennung in kennungen:
            zeile = v.execute("SELECT pdf_pfad, archiv_pdf FROM stellen WHERE id=?",
                              (int(kennung),)).fetchone()
            if not zeile:
                continue
            for spalte in ("pdf_pfad", "archiv_pdf"):
                pfad = zeile[spalte]
                if pfad and os.path.exists(pfad):
                    try:
                        os.remove(pfad)
                        entfernt += 1
                    except OSError:
                        pass
            v.execute("UPDATE stellen SET pdf_pfad=NULL, archiv_pdf=NULL WHERE id=?",
                      (int(kennung),))
    return entfernt


def favorit_setzen(kennungen, favorit=True):
    """Favoriten sind ein eigenes Merkmal, kein Status — eine beworbene Stelle
    darf gleichzeitig Favorit sein."""
    with verbinden() as v:
        v.executemany("UPDATE stellen SET favorit=? WHERE id=?",
                      [(1 if favorit else 0, int(k)) for k in kennungen])


def favoriten():
    """Alle Favoriten, dringendste Frist zuerst."""
    with verbinden() as v:
        return v.execute(
            "SELECT * FROM stellen WHERE favorit=1 AND status != ? "
            "ORDER BY frist IS NULL, frist ASC, punkte DESC", (VERWORFEN,)).fetchall()


def verlauf_setzen(kennung, beworben_am=None, rueckmeldung=None,
                   wiedervorlage=None):
    """Hält den Stand einer Bewerbung fest.

    Ohne das ist „beworben" eine Sackgasse: Man sieht, dass etwas raus ist,
    aber nicht wann, ob eine Antwort kam und wann man nachfassen wollte.
    """
    werte, felder = [], []
    for name, wert in (("beworben_am", beworben_am),
                       ("rueckmeldung", rueckmeldung),
                       ("wiedervorlage", wiedervorlage)):
        if wert is not None:
            felder.append(f"{name}=?")
            werte.append(wert or None)
    if not felder:
        return
    with verbinden() as v:
        v.execute(f"UPDATE stellen SET {', '.join(felder)} WHERE id=?",
                  werte + [int(kennung)])


def wiedervorlagen(bis=None):
    """Was heute (oder bis zum genannten Tag) ansteht."""
    stichtag = bis or date.today().isoformat()
    with verbinden() as v:
        return v.execute(
            "SELECT * FROM stellen WHERE wiedervorlage IS NOT NULL "
            "AND wiedervorlage != '' AND wiedervorlage <= ? AND status != ? "
            "ORDER BY wiedervorlage", (stichtag, VERWORFEN)).fetchall()


def abgelaufene(status=NEU, puffer_tage=0):
    """Stellen, deren Frist durch ist und die noch unbearbeitet herumliegen."""
    from datetime import timedelta
    grenze = (date.today() - timedelta(days=int(puffer_tage))).isoformat()
    with verbinden() as v:
        return v.execute(
            "SELECT * FROM stellen WHERE status=? AND frist IS NOT NULL "
            "AND frist != '' AND frist < ? ORDER BY frist", (status, grenze)).fetchall()


SICHERUNGEN = 7          # so viele Tagesstände werden aufgehoben


def sichern():
    """Legt eine Tageskopie der Datenbank an.

    Die Triage ist Handarbeit: Status, Notizen, Favoriten und Briefings stecken
    nur hier. Eine beschädigte Datei wäre der Verlust von Wochen. Die Kopie
    kostet Sekunden und ein paar Megabyte.
    """
    import shutil
    if not os.path.exists(DB_PFAD):
        return None
    ordner = os.path.join(os.path.dirname(DB_PFAD), "sicherungen")
    os.makedirs(ordner, exist_ok=True)
    ziel = os.path.join(ordner, f"stellenradar_{date.today().isoformat()}.db")
    if os.path.exists(ziel):
        return ziel          # heute schon gesichert
    with verbinden() as quelle:
        kopie = sqlite3.connect(ziel)
        try:
            quelle.backup(kopie)      # konsistent, auch wenn gerade geschrieben wird
        finally:
            kopie.close()
    # Alte Stände aufräumen
    staende = sorted(f for f in os.listdir(ordner) if f.endswith(".db"))
    for alt in staende[:-SICHERUNGEN]:
        try:
            os.remove(os.path.join(ordner, alt))
        except OSError:
            pass
    return ziel


def briefing_merken(kennung, text, modell):
    with verbinden() as v:
        v.execute("UPDATE stellen SET briefing=?, briefing_am=?, briefing_modell=? "
                  "WHERE id=?",
                  (text, datetime.now().isoformat(timespec="seconds"), modell,
                   int(kennung)))


def notiz_setzen(kennung, notiz):
    with verbinden() as v:
        v.execute("UPDATE stellen SET notiz=? WHERE id=?", (notiz, int(kennung)))


def pdf_merken(kennung, pfad):
    with verbinden() as v:
        v.execute("UPDATE stellen SET pdf_pfad=? WHERE id=?", (pfad, int(kennung)))


def archiv_merken(kennung, pfad):
    """Pfad der archivierten Originalseite festhalten."""
    with verbinden() as v:
        v.execute("UPDATE stellen SET archiv_pdf=? WHERE id=?", (pfad, int(kennung)))


def ohne_archiv():
    """Stellen, zu denen noch keine Seitenkopie existiert."""
    with verbinden() as v:
        return v.execute(
            "SELECT * FROM stellen WHERE status != ? "
            "AND (archiv_pdf IS NULL OR archiv_pdf = '') ORDER BY punkte DESC",
            (VERWORFEN,)).fetchall()


def endgueltig_loeschen(kennungen):
    """Entfernt Einträge wirklich. Nur für den Fall, dass jemand die Liste
    bewusst bereinigen will — die Triage benutzt 'verworfen'."""
    with verbinden() as v:
        v.executemany("DELETE FROM stellen WHERE id=?", [(int(k),) for k in kennungen])


# ----------------------------------------------------------------------------------
# LESEN
# ----------------------------------------------------------------------------------

def holen(status=None, feld=None, sektor=None, suche=None, sortierung="punkte"):
    """Liefert Stellen nach Filter. `status=None` heißt: alles außer verworfen."""
    bedingungen, werte = [], []
    if status:
        if isinstance(status, (list, tuple, set)):
            bedingungen.append(f"status IN ({', '.join('?' for _ in status)})")
            werte.extend(list(status))
        else:
            bedingungen.append("status=?")
            werte.append(status)
    else:
        bedingungen.append("status != ?")
        werte.append(VERWORFEN)
    if feld:
        bedingungen.append("(feld_haupt=? OR felder LIKE ?)")
        werte.extend([int(feld), f"%{int(feld)}%"])
    if sektor:
        bedingungen.append("sektor=?")
        werte.append(sektor)
    if suche:
        # Auch im Ausschreibungstext suchen. Ohne das findet „E-Akte" nichts,
        # obwohl der Begriff in mehreren Ausschreibungen steht.
        bedingungen.append("(titel LIKE ? OR arbeitgeber LIKE ? OR ort LIKE ? "
                           "OR volltext LIKE ? OR notiz LIKE ?)")
        werte.extend([f"%{suche}%"] * 5)

    ordnung = {
        "punkte": "punkte DESC, frist IS NULL, frist ASC",
        "frist": "frist IS NULL, frist ASC, punkte DESC",
        "neu": "gefunden_am DESC, punkte DESC",
        "arbeitgeber": "arbeitgeber COLLATE NOCASE, titel COLLATE NOCASE",
    }.get(sortierung, "punkte DESC")

    with verbinden() as v:
        return v.execute(
            f"SELECT * FROM stellen WHERE {' AND '.join(bedingungen)} "
            f"ORDER BY {ordnung}", werte).fetchall()


def eine(kennung):
    with verbinden() as v:
        return v.execute("SELECT * FROM stellen WHERE id=?", (int(kennung),)).fetchone()


def kennzahlen():
    """Zahlen fürs Dashboard."""
    heute = date.today()
    with verbinden() as v:
        zahlen = {s: 0 for s in STATUS_REIHE}
        for zeile in v.execute("SELECT status, COUNT(*) n FROM stellen GROUP BY status"):
            zahlen[zeile["status"]] = zeile["n"]
        offen = v.execute(
            "SELECT * FROM stellen WHERE status IN (?, ?) ORDER BY frist IS NULL, frist",
            (NEU, VORGEMERKT)).fetchall()
        felder = {}
        for zeile in v.execute(
                "SELECT feld_haupt, COUNT(*) n FROM stellen "
                "WHERE status != ? GROUP BY feld_haupt", (VERWORFEN,)):
            felder[zeile["feld_haupt"]] = zeile["n"]
        sektoren = {}
        for zeile in v.execute(
                "SELECT sektor, COUNT(*) n FROM stellen "
                "WHERE status != ? GROUP BY sektor", (VERWORFEN,)):
            sektoren[zeile["sektor"]] = zeile["n"]
        # Der letzte ABGESCHLOSSENE Lauf. Ein abgebrochener Eintrag ohne
        # Endzeit darf das Dashboard nicht auf „noch kein Suchlauf" setzen.
        letzter = v.execute(
            "SELECT * FROM laeufe WHERE beendet IS NOT NULL "
            "ORDER BY id DESC LIMIT 1").fetchone()

    # Fristen einteilen
    faecher = {"abgelaufen": [], "heute_morgen": [], "woche": [], "zwei_wochen": [],
               "spaeter": [], "ohne": []}
    for zeile in offen:
        if not zeile["frist"]:
            faecher["ohne"].append(zeile)
            continue
        try:
            tage = (date.fromisoformat(zeile["frist"]) - heute).days
        except ValueError:
            faecher["ohne"].append(zeile)
            continue
        if tage < 0:
            faecher["abgelaufen"].append(zeile)
        elif tage <= 1:
            faecher["heute_morgen"].append(zeile)
        elif tage <= 7:
            faecher["woche"].append(zeile)
        elif tage <= 14:
            faecher["zwei_wochen"].append(zeile)
        else:
            faecher["spaeter"].append(zeile)

    with verbinden() as v:
        anzahl_favoriten = v.execute(
            "SELECT COUNT(*) n FROM stellen WHERE favorit=1 AND status != ?",
            (VERWORFEN,)).fetchone()["n"]

    return {"status": zahlen, "felder": felder, "sektoren": sektoren,
            "fristen": faecher, "letzter_lauf": letzter,
            "favoriten": anzahl_favoriten,
            "gesamt": sum(zahlen.values())}


def tage_bis_frist(frist):
    """Tage bis zur Frist. None, wenn keine oder unlesbar."""
    if not frist:
        return None
    try:
        return (date.fromisoformat(frist) - date.today()).days
    except (ValueError, TypeError):
        return None


# ----------------------------------------------------------------------------------
# LÄUFE PROTOKOLLIEREN
# ----------------------------------------------------------------------------------

def lauf_beginnen():
    with verbinden() as v:
        # Einträge ohne Endzeit stammen von Läufen, die hart beendet wurden
        # (Programm geschlossen, Rechner aus). Sie würden sich sonst ansammeln.
        v.execute("DELETE FROM laeufe WHERE beendet IS NULL")
        zeiger = v.execute(
            "INSERT INTO laeufe (begonnen, quellen, gesehen, neu, verworfen) "
            "VALUES (?, 0, 0, 0, 0)", (datetime.now().isoformat(timespec="seconds"),))
        return zeiger.lastrowid


def lauf_beenden(kennung, quellen, gesehen, neu, verworfen, fehler=None):
    with verbinden() as v:
        v.execute(
            "UPDATE laeufe SET beendet=?, quellen=?, gesehen=?, neu=?, verworfen=?, "
            "fehler=? WHERE id=?",
            (datetime.now().isoformat(timespec="seconds"), quellen, gesehen, neu,
             verworfen, (fehler or "")[:4000], int(kennung)))


def laeufe(grenze=10):
    with verbinden() as v:
        return v.execute("SELECT * FROM laeufe ORDER BY id DESC LIMIT ?",
                         (int(grenze),)).fetchall()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    einrichten()
    k = kennzahlen()
    print(f"Datenbank: {DB_PFAD}")
    print(f"Stellen gesamt: {k['gesamt']}")
    for status, anzahl in k["status"].items():
        print(f"  {STATUS_NAMEN[status]:16} {anzahl}")
