# Arbeitsanweisung für diesen Projektordner

**Lies zuerst `UEBERGABE.md`.** Dort steht alles: Aufbau, Datenquellen,
Datenmodell, Stolperfallen, Wartung, offene Punkte.

## Was das hier ist

Der **Stellenradar** sucht Stellenausschreibungen passend zu einem
hinterlegten Profil — im öffentlichen Dienst Brandenburg und Berlin, beim
Bund, in der Wissenschaft und in Beratungshäusern für die öffentliche Hand —
und macht daraus eine überschaubare Arbeitsliste mit Fristen, Favoriten und
Bewerbungsverlauf.

**Das Profil steht nicht im Code**, sondern in `profil.json`,
`berufsfelder.json` und `gewichtung.json`. Die drei Dateien gehören der Person,
die das Programm benutzt, stehen deshalb in `.gitignore` und werden im Fenster
gepflegt. In `konfiguration.py` liegt nur ein neutrales Beispiel. **Niemals
personenbezogene Daten in eine `.py`-Datei schreiben.**

Python 3.14, Tkinter, SQLite, Scrapling. Rund 7.800 Zeilen in 18 Modulen.

## Immer die Projektumgebung benutzen

```bash
.venv\Scripts\python.exe stellenradar.py
```

Nie das globale Python. Beim Entwickeln `python.exe` statt `pythonw.exe` —
sonst sind Fehlermeldungen unsichtbar.

## Nach jeder Änderung

```bash
.venv\Scripts\python.exe stellenradar.py --selftest
```
```bash
.venv\Scripts\python.exe stellenradar.py --guitest
```

Beide müssen grün sein. Der GUI-Test arbeitet mit einer Wegwerf-Datenbank und
rührt die echten Daten nicht an.

## Sprache und Stil

- **Alles auf Deutsch**: Code, Kommentare, Variablennamen, Oberfläche,
  Dokumentation. Das ist durchgehend so und soll so bleiben.
- **Gendern** über neutrale Formen, sonst Doppelpunkt (Mitarbeiter:innen).
- **Kommentare erklären das Warum**, nicht das Was — besonders bei allem, was
  nach einem Umweg aussieht. Fast jeder Umweg im Code hat einen gemessenen
  Grund, der danebensteht.

## Arbeitsweise

1. **Nichts erfinden.** Keine Arbeitgeber, keine URLs, keine Zahlen ohne
   Prüfung. Jede Adresse im Register wurde wirklich abgerufen.
2. **Messen statt schätzen.** Wer etwas an der Erkennung ändert, misst die
   Wirkung an echten Daten — nicht an Vermutungen.
3. **Ehrlich berichten.** Wenn eine Seite nichts liefert, steht das so da, mit
   Begründung.
4. **Was der Mensch entschieden hat, bleibt unangetastet**: Status, Notizen,
   Favoriten, von Hand erfasste Stellen.

## Die häufigsten Stolperfallen

Vollständig in `UEBERGABE.md`, Abschnitt 10. Die vier, die am ehesten
zuschlagen:

- **`pythonw.exe` hat kein `sys.stdout`** — ein `reconfigure()` darauf tötet
  das Programm wortlos.
- **`re.IGNORECASE` macht auch `[A-ZÄÖÜ]` unwirksam** — Schalter mit `(?i:…)`
  auf die Signalwörter begrenzen.
- **`tk.Text` fordert 80 Zeichen Breite an** — nebeneinander `width=1` setzen.
- **`.ps1`-Dateien brauchen eine UTF-8-BOM**, sonst bricht die Syntax unter
  PowerShell 5.1.

## Wo du anfängst

| Du willst … | Datei |
|---|---|
| andere Stellen finden | `einordnung.py` — oder im Fenster unter „Berufsfelder" |
| die Sortierung ändern | im Fenster unter „Gewichtung" |
| einen Arbeitgeber ergänzen | `arbeitgeber.py` |
| eine neue Quelle anbinden | `quelle_berlin.py` als Muster, in `suche.py` einhängen |
| am Aussehen schrauben | `oberflaeche.py` |
| eine Ansicht ändern | `stellenradar.py` |
| das Briefing anders aufbauen | `briefing.py` |

## Wartungswerkzeuge

```bash
.venv\Scripts\python.exe pruefe_arbeitgeber.py
```
```bash
.venv\Scripts\python.exe finde_karriereseite.py https://www.beispiel.de
```
```bash
.venv\Scripts\python.exe erkunde_portale.py interamt
```

Gehören nicht zum laufenden Programm, sondern zur Pflege des Registers.
