# Mitmachen

Beiträge sind willkommen — besonders **neue Quellen** (andere Bundesländer,
andere Portale) und **Korrekturen am Arbeitgeberregister**.

---

## Bevor du etwas einreichst

### 1. Keine personenbezogenen Daten

Das ist die einzige harte Regel.

`profil.json`, `berufsfelder.json`, `gewichtung.json`, `stellenradar.db`,
`archiv/`, `steckbriefe/` und `sicherungen/` enthalten Lebenslauf, Bewerbungs-
stand und gesicherte Ausschreibungen. Sie stehen in `.gitignore` und gehören
dort hin. In `konfiguration.py` liegt ein neutrales Beispielprofil — **es
bleibt neutral.**

Vor dem Commit:

```bash
git status --porcelain --ignored | grep -E "profil|berufsfelder|gewichtung|\.db|archiv/|steckbriefe/"
```

Was hier auftaucht, muss als `!!` (ignoriert) markiert sein, nicht als `A`
oder `M`.

### 2. Beide Tests müssen grün sein

```bash
.venv\Scripts\python.exe stellenradar.py --selftest
```
```bash
.venv\Scripts\python.exe stellenradar.py --guitest
```

Der Oberflächentest arbeitet mit einer Wegwerf-Datenbank und rührt echte Daten
nicht an.

### 3. Änderungen an der Erkennung werden gemessen

Wer Stichworte, Ausschlüsse oder Punkte ändert, misst die Wirkung an echten
Daten statt sie zu schätzen:

```bash
.venv\Scripts\python.exe suche.py --nachfiltern
```
```bash
.venv\Scripts\python.exe suche.py --punkte-neu
```

In die Beschreibung des Pull Requests gehört, **was sich dadurch verschoben
hat** — wie viele Stellen zusätzlich durchkamen, wie viele herausfielen, und
ein, zwei Beispiele.

---

## Sprache und Stil

- **Alles auf Deutsch**: Code, Kommentare, Variablennamen, Oberfläche,
  Dokumentation, Commit-Nachrichten. Das ist durchgehend so und soll so
  bleiben.
- **Gendern** über neutrale Formen (Lehrende, Beschäftigte, Ansprechperson),
  sonst Doppelpunkt (Mitarbeiter:innen). Nicht Sternchen, nicht Binnen-I.
  Ausnahme: Zitate und amtliche Bezeichnungen bleiben wörtlich.
- **Kommentare erklären das Warum**, nicht das Was — besonders bei allem, was
  nach einem Umweg aussieht. Fast jeder Umweg hier hat einen gemessenen Grund,
  der danebensteht. Wer ihn nicht kennt, baut ihn zurück und den Fehler wieder
  ein.

---

## Eine neue Quelle anbinden

Das ist der häufigste sinnvolle Beitrag. `quelle_berlin.py` ist das kürzeste
Muster (181 Zeilen).

Ein Quellenmodul braucht genau zwei Dinge:

1. eine Funktion, die die Trefferliste durchblättert und Links liefert,
2. eine Funktion, die zu einem Link den Volltext holt.

Es kennt **weder die Einordnung noch die Oberfläche**. Eingehängt wird es in
`suche.py`.

Vorher lohnt `erkunde_portale.py` — es sagt dir, ob das Portal über einfaches
HTTP lesbar ist oder den Browser braucht.

**Bitte keine Anti-Bot- oder CAPTCHA-Umgehung.** Scrapling ist hier, weil es
JavaScript-Seiten liest, nicht weil es Schutzmechanismen aushebelt. Pull
Requests in diese Richtung werden nicht übernommen.

---

## Einen Arbeitgeber ergänzen

In `arbeitgeber.py`, als Zeile im passenden Block.

**Adressen nicht raten.** Von 123 geratenen Karriereseiten waren seinerzeit 38
tote Links. Stattdessen:

```bash
.venv\Scripts\python.exe finde_karriereseite.py https://www.beispiel.de
```

Das sucht die echte Karriereseite und ruft sie zur Probe ab. Danach:

```bash
.venv\Scripts\python.exe pruefe_arbeitgeber.py
```

Liefert eine Seite nichts, gehört sie nicht stillschweigend ins Register,
sondern mit Begründung nach `NICHT_AUFGENOMMEN` — diese Liste ist Teil des
Codes und erspart dem nächsten Menschen die Arbeit.

---

## Stolperfallen

Die vollständige Liste steht in `UEBERGABE.md`, Abschnitt 10. Die vier, die am
ehesten zuschlagen:

- **`pythonw.exe` hat kein `sys.stdout`.** Ein `reconfigure()` darauf tötet
  das Programm wortlos — aus der Shell gestartet läuft es, per Verknüpfung
  nicht.
- **`re.IGNORECASE` macht auch `[A-ZÄÖÜ]` unwirksam.** Den Schalter mit
  `(?i:…)` auf die Signalwörter begrenzen.
- **`tk.Text` fordert 80 Zeichen Breite an.** Nebeneinander `width=1` setzen,
  sonst bekommt das erste Feld alles.
- **`.ps1`-Dateien brauchen eine UTF-8-BOM.** Ohne sie liest PowerShell 5.1
  die Datei als ANSI, die Umlaute zerfallen und die Syntax bricht — das
  Skript startet gar nicht.

---

## Lizenz

Mit dem Einreichen eines Beitrags stimmst du zu, dass er unter der
MIT-Lizenz veröffentlicht wird (siehe `LICENSE`).

Bitte **keine Abhängigkeiten unter Copyleft-Lizenzen** hinzufügen. `pymupdf`
wurde aus genau diesem Grund entfernt: Es steht unter AGPL-3.0 und hätte das
ganze Programm darunter gezwungen.
