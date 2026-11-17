# Stellenradar

Ein Stellen-Crawler für den **öffentlichen Dienst und die Public-Sector-Beratung
im Raum Berlin/Brandenburg**. Er durchsucht drei Portaltypen, ordnet jede
Ausschreibung einem Berufsfeld zu, vergibt Passungs-Punkte, sichert die
Ausschreibungsseite als PDF, bevor sie offline geht, und führt die Bewerbung
von „neu" bis „beworben".

Gebaut, weil Stellenportale des öffentlichen Dienstes drei Dinge gemeinsam
haben: Sie sind zahlreich, sie sind schlecht durchsuchbar, und sie nehmen
Ausschreibungen nach Fristende offline.

Was er gegenüber einem einfachen Crawler mehr kann:

| | Was |
|---|---|
| **Drei Quellen statt einer** | Interamt (Umkreissuche), Karriereportal Berlin, 93 geprüfte Arbeitgeberseiten |
| **Volltext statt Titel** | erkennt auch die Stelle, deren Thema erst im dritten Aufzählungspunkt steht |
| **Archiv-PDF je Stelle** | die Ausschreibungsseite, gesichert bevor sie offline geht |
| **PDF-Steckbrief je Stelle** | alle Angaben plus vollständiger Ausschreibungstext |
| **Passungs-Punkte** | sortiert die Liste nach Eignung — die Gewichtung stellst du selbst ein |
| **Triage mit Verlauf** | neu → vorgemerkt → beworben, mit Fristen-Ampel und Wiedervorlage; verworfene Stellen kommen nie wieder |
| **Briefing je Favorit** | lokale KI (Ollama), strikt an Ausschreibungstext und Profil gebunden — optional |

Deutschsprachig durchgehend: Oberfläche, Code, Kommentare, Dokumentation.
Läuft auf einem Windows-Rechner, ohne Server, ohne Konto, ohne Cloud.

## Wegweiser

| Du willst … | Lies |
|---|---|
| das Programm benutzen | weiter hier, und `LIESMICH.txt` für die Kurzfassung |
| wissen, **warum** es so gebaut ist | [`KONZEPT.md`](KONZEPT.md) |
| daran entwickeln | [`UEBERGABE.md`](UEBERGABE.md) — Module, Datenmodell, Stolperfallen |
| etwas beitragen | [`CONTRIBUTING.md`](CONTRIBUTING.md) |

## Beim ersten Start: das eigene Profil eintragen

Ausgeliefert wird ein **neutrales Beispielprofil**. Solange es gilt, sortiert
das Programm nach fremden Maßstäben und das KI-Briefing hat keine Belege.

Also zuerst im Fenster unter **Berufsfelder**:

1. die sechs Berufsfelder umbenennen und ihre Stichworte anpassen,
2. die eigenen Kompetenzen je Feld eintragen — Belege aus dem Lebenslauf,
3. unter **Profil** Werdegang, Stärken und Weiterbildungen,
4. unter **Gewichtung**, was dir wichtiger ist: Nähe oder Bezahlung.

Das landet in `profil.json`, `berufsfelder.json` und `gewichtung.json` neben
dem Programm. Wie man das auf eine andere Region oder Branche dreht, steht in
[`KONZEPT.md`](KONZEPT.md), Abschnitt 5.

> **Alle Daten bleiben auf dem Rechner.** Es gibt kein Konto, keine
> Übertragung und keine Cloud-KI. Die drei Profildateien, die Datenbank und
> das Archiv stehen in `.gitignore` — sie gehören der Person, die das
> Programm benutzt, und dürfen nicht in ein Repository geraten.

## Auf einen neuen Rechner bringen

Ordner kopieren, **`INSTALLIEREN.bat`** doppelklicken, fertig. Das Skript
(`_setup\installieren.ps1`) macht in sieben Schritten alles:

| Schritt | Was passiert |
|---|---|
| 1 | Rechner prüfen: Windows, 64 Bit, Arbeitsspeicher, Platz |
| 2 | Python finden — oder die mitgelieferte Fassung installieren (`_setup\python-3.14.7-amd64.exe`, Signatur der Python Software Foundation geprüft) |
| 3 | Programmumgebung anlegen und die Pakete laden |
| 4 | Browser zum Auslesen der Portale (zwei Chromium-Fassungen, rund 400 MB) |
| 5 | Chrome oder Edge für die PDF-Erzeugung suchen |
| 6 | Lokale KI — nur auf Nachfrage, abhängig vom Arbeitsspeicher |
| 7 | Selbsttest, Oberflächentest, Desktop-Symbol |

**Administratorrechte sind nicht nötig.** Python installiert sich nur für den
angemeldeten Benutzer, Ollama ebenso. Dauer: 15 bis 40 Minuten.

### Welches KI-Modell der Installer vorschlägt

Ein Modell braucht im Betrieb grob das Doppelte seiner Dateigröße an
Arbeitsspeicher. Deshalb staffelt der Installer:

| Arbeitsspeicher | Modell | Anmerkung |
|---|---|---|
| ab 16 GB | `gemma4:12b` | beste Textqualität |
| 12–16 GB | `qwen3.5:9b` | gute Qualität |
| 8–12 GB | `qwen3.5:2b` | sparsam, braucht mehrere Minuten je Kurzinfo, formuliert einfacher |
| unter 8 GB | keines | das Programm läuft vollständig ohne — „Eckdaten ohne KI" |

### Die weiteren Knöpfe

| Datei | Wofür |
|---|---|
| `PRUEFEN.bat` | sagt in Klartext, was da ist und was fehlt — ändert nichts |
| `KI_NACHINSTALLIEREN.bat` | holt Ollama und das passende Modell nach |
| `BROWSER_NACHINSTALLIEREN.bat` | holt die Auslese-Browser nach |
| `Stellenradar_starten.bat` | der Starter, den das Desktop-Symbol aufruft |

### Eine Falle, die beim Testen auffiel

Die `.ps1`-Dateien **müssen mit Byte-Order-Mark gespeichert sein.** PowerShell
5.1 liest eine Datei ohne BOM als ANSI; die deutschen Umlaute zerfallen dann so,
dass die Syntax bricht — das Skript startet gar nicht erst. Als UTF-8 gelesen
waren dieselben Dateien fehlerfrei. Wer hier etwas ändert, muss die BOM
erhalten.

**Bedienung in einem Satz:** Oben auf „🔍 Suchlauf starten", danach im Reiter
„🆕 Neu" jede Stelle entweder vormerken (⭐) oder verwerfen (🗑). Verworfene
kommen nie wieder.

## Umgebung

Eine eigene `.venv` im Projektordner, nie das globale Python. `INSTALLIEREN.bat`
legt sie an; von Hand geht es so:

```bash
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m scrapling install
```

Enthalten: `scrapling[fetchers]` 0.5.1, `pypdf`, `pymupdf`. Die Browser landen
unter `%LOCALAPPDATA%\ms-playwright` und brauchen rund 400 MB. Danach:

```bash
.venv\Scripts\python.exe stellenradar.py --selftest
```

## Die Quellen

### Interamt — die wichtigste Einzelquelle

Eine Umkreissuche um **PLZ 14467 (Potsdam)** erfasst Berlin, Potsdam und
Umgebung in einem Durchgang: **828 Stellen** am 11.11.2026. Die Trefferliste
liefert pro Stelle schon Behörde, Bezeichnung, Besoldung, Entgelt, PLZ/Ort,
**Entfernung in km**, Dienstort, Einstelldatum und **Bewerbungsfrist**.

```bash
.venv\Scripts\python.exe quelle_interamt.py 25
```

Drei Eigenheiten, die den Code bestimmen (alle am lebenden Portal ermittelt):

1. Apache-Wicket-Anwendung. Der Suchknopf lässt sich nicht zuverlässig
   anklicken — **Enter im PLZ-Feld** schickt die Suche ab.
2. Die Liste blättert nicht, sie lädt nach: **10 Zeilen je Klick auf
   „mehr laden"**. Im DOM stehen 20 `tbody tr`, aber nur 10 sind Datenzeilen.
3. Der **Cookie-Hinweis klebt am Seitenende und verdeckt genau diesen Knopf**.
   Ohne Schließen läuft jeder Klick in eine Zeitüberschreitung. Interamt setzt
   nach eigener Angabe ausschließlich notwendige Cookies, deshalb ist
   Bestätigen hier die datensparsame Antwort.

Detailseiten haben eine feste Adresse (`…/koop/app/stelle?id=NUMMER`) und
lassen sich **ohne Browser** abrufen — schnell und schonend.

### Karriereportal Berlin — die zweite große Quelle

```bash
.venv\Scripts\python.exe quelle_berlin.py 32
```

Bündelt Senatsverwaltungen, die zwölf Bezirksämter, Polizei, Feuerwehr und die
nachgeordneten Behörden: **629 Stellen** am 12.11.2026.

Als eine von 93 Karriereseiten behandelt lieferte das Portal **genau einen
Treffer** — weil die Übersicht nur die ersten rund 15 Stellen zeigt. Es blättert
aber über einen schlichten Parameter in der Adresse (`?start=0`, `?start=20`, …)
und braucht dafür **keinen Browser**. Als eigene Quelle gelesen: 526 Stellen
geprüft, **8 passende gefunden** — darunter „Sachbearbeitung im Rahmen des
E-Government und der Digitalisierung" beim Bezirksamt Neukölln und „Mitarbeit im
Projektbüro für Digitalisierungsprojekte" bei der Senatsverwaltung für Bildung.

Die ausschreibende Behörde steht nicht in der Übersicht, wohl aber im Detailtext
— sonst stünde bei allen 600 Stellen nur „Land Berlin".

### 93 Arbeitgeberseiten

```bash
.venv\Scripts\python.exe arbeitgeber.py          # Register anzeigen
.venv\Scripts\python.exe pruefe_arbeitgeber.py   # alle URLs prüfen
```

| Gruppe | Anzahl |
|---|---|
| Öffentlicher Dienst Brandenburg | 35 |
| Wissenschaft Potsdam | 11 |
| Öffentlicher Dienst Berlin | 16 |
| Wissenschaft Berlin | 8 |
| Bund | 6 |
| Public-Sector-Beratung | 17 |

Prüflauf am 11.11.2026: **77 von 93 zeigen Ausschreibungen**, keine toten Links.
Die übrigen 16 sind erreichbar, hatten aber nichts offen oder brauchen den
Browser (im Register als `tief` markiert: Landeshauptstadt Potsdam, ProPotsdam,
HPI, HU Berlin, ZenDiS).

**20 Arbeitgeber wurden bewusst nicht aufgenommen** — mit Begründung in
`arbeitgeber.py` unter `NICHT_AUFGENOMMEN`. Kurz: Capgemini, Accenture,
Deloitte, KPMG, Kienbaum, adesso, T-Systems und IBM haben ihre Stellensuche
hinter JavaScript-Portalen ohne feste Adresse; BVG, BSR und die Sparkassen
haben keine auffindbare Stellenübersicht; die meisten Bundesministerien
schreiben ohnehin über Interamt aus. Lieber ein ehrlich kurzes Register als
Einträge, die dauerhaft null Treffer liefern.

Karriereseiten wurden **nicht geraten**, sondern gesucht:

```bash
.venv\Scripts\python.exe finde_karriereseite.py https://www.bsr.de
.venv\Scripts\python.exe finde_karriereseite.py --aus-bericht
```

## Suchlauf

```bash
.venv\Scripts\python.exe suche.py
```

| Schalter | Wirkung |
|---|---|
| `--runden N` | Nachladerunden bei Interamt (Standard 25 ≈ 260 Stellen) |
| `--gruendlich` | lädt auch Stellen ohne Berufsfeld-Treffer im Titel |
| `--nur-interamt` | nur Interamt |
| `--nur-seiten` | nur die Arbeitgeberseiten |
| `--nachfiltern` | prüft die **gespeicherten** Stellen noch einmal gegen die aktuellen Regeln |
| `--punkte-neu` | rechnet alle Punkte mit der aktuellen Gewichtung neu |
| `--eckdaten-neu` | zieht Frist, Entgelt und Kontakt noch einmal aus den gespeicherten Texten |

**`--nachfiltern`** ist gedacht für den Fall, dass die Stichwortlisten in
`einordnung.py` nachgeschärft werden: Die alten Fehltreffer verschwinden dann
auch aus der Liste, und die Punkte werden neu gerechnet. Angefasst werden
ausschließlich Stellen im Status „neu" — was schon vorgemerkt, beworben oder
bewusst verworfen wurde, bleibt unangetastet.

**Zwei Betriebsarten, weil Gründlichkeit Zeit kostet:**

- **schnell** (Standard): Nur Kandidaten, deren **Titel** ein Berufsfeld
  trifft, werden im Detail geladen. Verpasst Stellen mit nichtssagendem Titel
  („Sachbearbeitung im Referat 23").
- **gründlich**: Jede nicht hart ausgeschlossene Stelle wird geladen und am
  Volltext geprüft. Findet mehr, dauert deutlich länger.

## Einordnung

`einordnung.py` ist das Herzstück. Die Felder selbst stehen seit dem Umbau
nicht mehr im Code, sondern in `berufsfelder.json` — bearbeitbar im Fenster
unter **Berufsfelder** (siehe unten).

**Sechs Berufsfelder** aus der Berufsfeld-Analyse vom 27.07.2026, jetzt mit
**gewichteten** Stichworten (3 = sehr aussagekräftig, 1 = schwaches Signal):

① Digitalisierung & E-Government · ② IT-Produkt- & Anforderungsmanagement ·
③ Projektleitung/PMO · ④ Prozess- & Changemanagement · ⑤ Kunden- &
Servicemanagement · ⑥ Wissenschafts- & Fördermanagement

**Kein Treffer ⇒ verworfen.** Harte Ausschlüsse haben immer Vorrang.

**Passungs-Punkte** (0 bis etwa 30) sortieren die Liste. Sie ersetzen kein
Urteil, sie sparen Lesezeit. Jede Stelle trägt ihre Begründung mit, etwa:
`Berufsfeld-Treffer: +7 | Region Berlin: +4 | E 13: +4 | unbefristet: +3`

Bewertet werden: Stärke des Berufsfeld-Treffers, mehrere Felder gleichzeitig,
Region (Potsdam 5 / Berlin 4 / Brandenburg 2), Sektor, Entgeltgruppe
(E 11–E 14 und A 12–A 14 am höchsten), unbefristet (+3) gegen befristet (−1),
Leitungs- oder Stabsfunktion, vorhandene Frist.

### Nach dem ersten Probelauf nachgeschärft

| Befund | Maßnahme |
|---|---|
| „Kinderschutzkoordinator:in" kam durch | `koordinator`/`koordination` als eigenständige Stichworte entfernt |
| „Projektleitung Verfahrenstechnik", „Koordination Baumaßnahmen" | 26 neue Ausschlüsse (Bau, Technik, Soziales) |
| Entgeltgruppe „E 17" erkannt, die es nicht gibt | `entgelt_pruefen()` mit Obergrenzen E 15 / A 16 / B 11 |
| „Frau Dr. Katrin Mueller" wurde zu „Frau Dr" | `re.IGNORECASE` machte `[A-ZÄÖÜ]` unwirksam → Schalter auf die Signalwörter begrenzt |

## PDF-Steckbriefe

```bash
.venv\Scripts\python.exe steckbrief.py            # die drei bestbewerteten
.venv\Scripts\python.exe steckbrief.py --dossier  # alle vorgemerkten in einem PDF
```

- **Steckbrief je Stelle**: Kopf mit Arbeitgeber, Titel und Marken (Punkte,
  Frist mit Restlaufzeit in Ampelfarbe, Berufsfelder, Sektor), Eckdaten-Tabelle,
  Begründung der Punkte, eigene Notiz, **vollständiger Ausschreibungstext**,
  Link und Erzeugungsdatum. So bleibt die Stelle lesbar, auch wenn die Seite
  im Netz längst offline ist — genau der Grund für diese Anforderung.
- **Dossier**: alle vorgemerkten und beworbenen Stellen in einem Dokument,
  **Fristenübersicht vorneweg**, nach Dringlichkeit gruppiert. Zum Ausdrucken.

Erzeugt über HTML → Chrome headless → `pypdf` für die Metadaten. Zwei
Stolperfallen sind im Code vermerkt: Chrome braucht eine ausdrückliche
`file:///`-Adresse mit Schrägstrichen, und bei einem **Leerzeichen im Zielpfad
schreibt Chrome die Datei nicht** — was bei Windows-Benutzerordnern (`C:\Users\
Max Mustermann\…`) der Normalfall ist. Deshalb wird immer im Temp-Ordner
gerendert und die fertige Datei danach kopiert.

Farbwelt: ein eigener, zurückhaltender Satz (`#03305D`, `#6B8E3D`, Calibri) —
bewusst kein Firmen- oder Hochschul-CI, denn das sind private
Fakultätsdokument.

## Datenhaltung

`stellenradar.db` (SQLite). Der wichtigste Unterschied zum Vorläufer: **Eine
gelöschte Stelle ist nicht weg, sondern bekommt den Status „verworfen"** und
wird nie wieder vorgeschlagen. Sonst sortiert man dieselbe Stelle jede Woche
erneut aus.

| Status | Bedeutung |
|---|---|
| 🆕 neu | frisch gefunden |
| ⭐ vorgemerkt | kommt auf die Merkliste und ins Dossier |
| ✉ beworben | Bewerbung ist raus |
| 🗑 verworfen | nicht interessant, kommt nie wieder |

Beim erneuten Fund einer bekannten Stelle werden nur die Sachangaben
aufgefrischt — Status und Notiz bleiben, denn das ist die Arbeit des Menschen.

## Rücksicht

Erkennbare Browserkennung, Pausen zwischen den Abrufen (0,8 s je Arbeitgeber,
0,45 s je Detailseite), höchstens 25 Treffer je Arbeitgeber und Lauf. Gedacht
für die **persönliche Stellensuche**; bitte robots.txt und Nutzungsbedingungen
beachten und nicht mehrmals täglich laufen lassen. Anti-Bot-Umgehung und
CAPTCHA-Lösen werden bewusst nicht genutzt.

## Die Oberfläche

Dunkle Seitenleiste links, heller Inhaltsbereich mit weißen Karten rechts —
acht Ansichten:

| Ansicht | Inhalt |
|---|---|
| **Dashboard** | Kennzahlen, Fristen-Ampel, „Das steht als Nächstes an", Verteilung nach Berufsfeld und Bereich |
| **Neu** | frisch gefundene Stellen — hier wird sortiert |
| **Vorgemerkt** | die Merkliste, Grundlage für das Dossier |
| **Beworben** | laufende Bewerbungen |
| **Verworfen** | Papierkorb, jederzeit zurückholbar |
| **Berufsfelder** | Felder, Stichworte und Kompetenzen ansehen und ändern |
| **Gewichtung** | wie viele Punkte wofür — Nähe oder Entgelt, je nach Lage |
| **Favoriten** | die ausgewählten Stellen mit Vorbereitungs-Briefing |
| **Archiv** | die gesicherten Ausschreibungsseiten |

**Die Fristen-Ampel** ist das Herzstück des Dashboards: abgelaufen · heute oder
morgen · diese Woche · in zwei Wochen · später · ohne Fristangabe. Ein Klick
springt in die nach Frist sortierte Liste.

**Das Suchfeld durchsucht auch den Ausschreibungstext und die Notizen** —
„E-Akte" findet Stellen, die den Begriff nur im Fließtext nennen.

**In jeder Liste**: Filterzeile (Suchwort, Berufsfeld, Bereich, Sortierung),
farbige Fristen, Vorschau des Ausschreibungstexts samt Punkte-Begründung, und
die Knöpfe ⭐ Vormerken · ✉ Beworben · 🗑 Verwerfen · 🌐 Im Browser ·
📄 Steckbrief · 📑 Seite als PDF · 📝 Notiz. Die Spalte **PDF** zeigt mit ✓,
ob die Originalseite schon gesichert ist.

Mehrfachauswahl mit Strg oder Umschalt, **Strg+A** markiert alles, **Entf**
verwirft, **Doppelklick** öffnet im Browser, **Rechtsklick** zeigt ein Menü.

Das Zahnrad oben rechts öffnet die Einstellungen für den Suchlauf: gründlich
suchen, welche Quellen laufen, ob automatisch archiviert wird, und die Zahl
der Interamt-Nachladerunden.

## Punkte selbst vergeben

Ansicht **Gewichtung**. Hier entscheidet sich, was eine Stelle „wert" ist.

**Schnell umstellen** setzt eine Grundhaltung:

| Vorlage | Wirkung |
|---|---|
| 🏠 Nähe ist wichtig | Potsdam und Babelsberg auf 10, Bundesweit auf −3, Entgelt fast neutral |
| 💶 Bezahlung ist wichtig | E 13/E 14 auf 9–10, E 9 auf −4, Regionen gedeckelt |
| 🎯 Fachliche Passung zählt | Berufsfeld-Obergrenze auf 16, alles andere zurück |
| ⚖ Ausgewogen | der Auslieferungszustand |

Darunter lässt sich **jeder Wert einzeln** einstellen: Punkte je Region, je
Entgeltgruppe, je Bereich, dazu Zuschläge für unbefristet, Leitungsfunktion,
mehrere Berufsfelder und vorhandene Frist. Negative Zahlen werten ab.

Nach dem Speichern werden **alle gespeicherten Stellen neu bewertet** — die
Sortierung passt sich sofort an. Die Begründung steht je Stelle in der
Vorschau, zum Beispiel:
`Berufsfeld-Treffer: +5 | Region Berlin: +4 | A 14: +3 | unbefristet: +3`

Gespeichert wird in **`gewichtung.json`** neben dem Programm.

## Berufsfelder und Kompetenzen bearbeiten

Ansicht **Berufsfelder**. Links die sechs Felder und „Mein Profil", rechts die
Bearbeitung.

Je Berufsfeld:

- **Bezeichnung** — frei änderbar
- **Stichworte** in drei Gewichtsstufen nebeneinander. Ein Stichwort je Zeile,
  klein geschrieben; Wortstämme genügen („projektleit" findet auch
  Projektleiterin und Projektleitung). Je höher das Gewicht, desto mehr Punkte
  gibt der Treffer.
- **Meine Kompetenzen in diesem Feld** — die Belege aus dem Lebenslauf. Nach
  einer Weiterbildung hier eine Zeile ergänzen.

Unter **Mein Profil** stehen Werdegang, übergreifende Stärken und ein eigener
Abschnitt **Weiterbildungen und Zertifikate**.

Nach dem Speichern der Stichworte fragt das Programm, ob die bereits
gefundenen Stellen noch einmal gegen die neuen Regeln geprüft werden sollen.
Angefasst wird dabei nur, was auf „neu" steht.

Gespeichert wird in **`berufsfelder.json`** und **`profil.json`**. Ein Knopf
stellt den Auslieferungszustand wieder her.

## Der Bewerbungsprozess

Oben im Dashboard steht **„⏰ Das wartet auf dich"** — fällige Wiedervorlagen
und abgelaufene Stellen, die noch unbearbeitet herumliegen. Beides geht sonst
unter.

**Verlauf** (Knopf in „Vorgemerkt" und „Beworben") hält fest:

| Feld | Wofür |
|---|---|
| Beworben am | wann die Bewerbung raus ist — Knopf „heute" |
| Rückmeldung | Eingangsbestätigung, Einladung, Zweitgespräch, Zusage, Absage … |
| Wiedervorlage | „erinnere mich an diesem Tag" — Knöpfe für 1, 2 und 4 Wochen |

Wer ein Bewerbungsdatum einträgt, dessen Stelle wandert automatisch nach
„Beworben". Der Reiter zeigt dort statt Punkten und Berufsfeld den Verlauf:
Bewerbungsdatum, Rückmeldung und Wiedervorlage mit Restlaufzeit.

**Abgelaufene Stellen** bleiben nicht ewig liegen: Das Dashboard bietet
„Aufräumen" an, das verwirft sie samt ihrer Dokumente.

## Stellen von Hand erfassen

Knopf **„＋ Stelle erfassen"** oben rechts. Nicht alles kommt über die Portale —
ein Hinweis aus dem Bekanntenkreis, ein Fund auf LinkedIn, eine Ausschreibung
per Mail. Ohne diesen Weg lebt so eine Stelle außerhalb des Programms: kein
Briefing, keine Seitenkopie, keine Frist im Dashboard.

Zwei Wege:

- **Link einfügen** → die Seite wird abgerufen, der Text gezogen, die Eckdaten
  erkannt. Danach wird angeboten, die Seite gleich als PDF zu sichern.
- **Text einfügen** → wenn die Seite eine Anmeldung verlangt oder sich nicht
  abrufen lässt. Die erste Zeile gilt als Stellenbezeichnung.

Die Stelle bekommt die Quelle „von Hand" und wird **von keinem Suchlauf
aussortiert** — bei einer selbst eingetragenen Stelle hat der Mensch
entschieden, nicht der Stichwortfilter. Trifft sie kein Berufsfeld, landet der
Hinweis in der Notiz statt im Papierkorb.

## Sicherung

Beim Start legt das Programm eine Tageskopie der Datenbank unter
`sicherungen\` ab und hebt die letzten sieben auf. Die Triage ist Handarbeit —
Status, Notizen, Favoriten und Briefings stecken nur in dieser einen Datei.

## Favoriten und Briefing

Stellen, die wirklich infrage kommen, bekommen in jeder Liste mit **★ Favorit**
einen Stern (oder per Rechtsklick). Die Spalte **★** zeigt ihn an. Favorit ist
ein eigenes Merkmal, kein Status — eine beworbene Stelle darf gleichzeitig
Favorit sein.

In der Ansicht **Favoriten** schaltet man links durch, rechts steht alles zu
dieser Stelle:

| Abschnitt | Woher |
|---|---|
| ① Key Facts zur Stelle | aus der Datenbank — Entgelt, Umfang, Befristung, Ort, Entfernung, Frist mit Restlaufzeit, Punkte samt Begründung, Link |
| ② Ansprechpartner | aus der Ausschreibung — Name, Telefon, E-Mail |
| ③ Meine hinterlegten Kompetenzen | die Belege, die unter **Berufsfelder** eingetragen sind |
| ④ Was die Stelle verlangt | KI, streng am Ausschreibungstext |
| ⑤ Wo meine Kompetenzen passen | KI: Anforderung → Beleg |
| ⑥ Der Elefant im Raum | KI: mögliche Lücken und wie sie sich drehen lassen |
| ⑦ Zum Arbeitgeber | KI aus ihrem Allgemeinwissen — **als ungeprüft gekennzeichnet** |
| ⑧ Fragen fürs Gespräch | KI |

**Die Trennung ist Absicht.** ① bis ③ stammen direkt aus der Ausschreibung
beziehungsweise aus dem eigenen Profil und stimmen. Alles ab ④ hat die lokale
KI geschrieben; besonders ⑦ kommt aus ihrem Allgemeinwissen und kann veraltet
oder falsch sein. Ein Hinweis am Ende sagt das noch einmal.

**„Eckdaten ohne KI"** erzeugt nur ① bis ③ — sofort und ohne Ollama.

### Die lokale KI

Läuft über **Ollama** auf dem eigenen Rechner, es verlässt nichts das Gerät.
Das Programm startet den Dienst selbst, wenn er nicht läuft, und nimmt das
beste installierte Modell: `gemma4:12b`, sonst `qwen3.5:9b`, sonst
`qwen3.5:2b`. Rechnen dauert auf der CPU einige Minuten je Stelle; das
Ergebnis wird gespeichert und nur auf Knopfdruck neu erzeugt.

Drei Härtungen aus dem Vorgängerprojekt stecken im Code:

- `gemma4:12b` ist ein Reasoning-Modell und liefert **leeren** Inhalt, wenn man
  `think` nicht abschaltet.
- Ein zu kleines `num_ctx` schneidet den Prompt **stillschweigend** vorne ab —
  also genau dort, wo Werdegang und Kompetenzen stehen.
- Kleine Modelle erfinden Fakten. Deshalb bekommt die KI alles Prüfbare
  vorgegeben und wird per Systemtext an Ausschreibung und Profil gebunden.
  Denkprozess und Markdown werden aus der Antwort entfernt.

## Das Archiv

**Portale nehmen Ausschreibungen nach Fristende offline, oft ohne Vorwarnung.**
Danach ist nicht mehr nachvollziehbar, worauf man sich beworben hat. Deshalb
sichert der Stellenradar zu jeder gefundenen Stelle automatisch die
Originalseite als PDF — direkt im Anschluss an den Suchlauf.

Zwei Dokumente je Stelle:

| Datei | Inhalt |
|---|---|
| `archiv\…_Originalseite.pdf` | die Seite, wie sie im Browser aussieht, mit Links |
| `steckbriefe\….pdf` | die aufbereiteten Eckdaten plus Volltext |

**Beim Verwerfen werden die Dokumente mitgelöscht** — Steckbrief, Seitenkopie
und Briefing. Was man aussortiert hat, braucht man nicht, und sonst wächst der
Ordner mit Unterlagen zu Stellen voll, die nie infrage kamen.

Holt man eine verworfene Stelle später zurück, steht sie ohne Dokumente da und
lässt sich neu sichern — die Originalseite ist dann allerdings vielleicht schon
offline. Alles andere bleibt dauerhaft liegen.

Die Ansicht **Archiv** zeigt Anzahl, Speicherplatz und welche Stellen noch
keine Kopie haben, und sichert sie auf Knopfdruck nach. Gemessen: 7 bis 10
Sekunden je Seite, 200 KB bis 1 MB je PDF.

Erzeugt über Chrome im Hintergrund (`--headless=new --print-to-pdf`). Braucht
also Chrome oder Edge; fehlt beides, sagt das Programm es.

## Selbsttests

```bash
.venv\Scripts\python.exe stellenradar.py --selftest
```
```bash
.venv\Scripts\python.exe stellenradar.py --guitest
```

Der GUI-Test baut das Fenster mit einer Wegwerf-Datenbank auf und prüft
Reiter, Filter, Triage und Dashboard — ohne die echten Daten anzufassen.

## Wenn das Programm nicht startet

Beim Start über das Desktop-Symbol läuft es ohne Konsolenfenster
(`pythonw.exe`). Stürzt es dabei ab, schreibt es den Grund nach **`fehler.log`**
und zeigt ihn in einem Fenster. Gibt es die Datei nicht, ist es sauber
gestartet.

Ein Fallstrick, der genau hier schon zugeschlagen hat: Ohne Konsole ist
`sys.stdout` leer. Jede Protokollzeile — auch die von Scrapling während des
Suchlaufs — bräuchte dann ein Ziel und würde das Programm sonst wortlos
beenden. Deshalb leitet `_stdout_vorbereiten()` beide Ströme notfalls nach
`lauf.log` um. Zum Nachsehen hilft immer:

```bash
.venv\Scripts\python.exe stellenradar.py
```

Mit `python.exe` statt `pythonw.exe` erscheint jede Meldung im Fenster.

## Was die Seiten tatsächlich liefern

Vollständige Messung aller 93 Arbeitgeberseiten am 12.11.2026:

| Befund | Anzahl | Bedeutung |
|---|---|---|
| Stellen da, aber kein Berufsfeld getroffen | 57 | der Filter arbeitet — die haben Stellen, nur keine passenden |
| keine Ausschreibungen erkennbar | 17 | siehe unten |
| liefert passende Stellen | 12 | |
| nur profilfremde Stellen | 7 | alles durch die harten Ausschlüsse gefiltert |

Abrufweg: 67 Seiten über HTTP, 26 brauchen den Browser.

**Die 17 stummen Seiten** liefern auch mit Browser nichts: MWFK, Landesbetrieb
Straßenwesen, Studierendenwerk, DIKOM, IHK Potsdam, Fraunhofer IAP, HOWOGE,
Deutsche Rentenversicherung, Stiftung Preußischer Kulturbesitz, DIW Berlin,
Bundesverwaltungsamt, RKI, ZenDiS, Materna, Zebralog, Detecon, PwC. Teils ist
gerade nichts offen, teils steckt die Liste hinter einer Suchmaske ohne feste
Adresse. Sie bleiben im Register — wenn dort etwas ausgeschrieben wird, taucht
es auf.

### Hat Scrapling das Auslese-Problem gelöst?

**Teilweise, und zwar messbar.**

Das **Bewerberportal der Landeshauptstadt Potsdam** (GWT-Anwendung) blieb beim
alten Crawler leer — auch nach 30 Sekunden, auch mit sichtbarem Browser.
Scrapling/Patchright liest es: **23 erkannte Ausschreibungen**. Auch ProPotsdam,
das HPI-Portal und die HU Berlin funktionieren jetzt.

**Aber:** Bei drei Arbeitgebern zeigt der Link auf die Übersichtsseite statt auf
die einzelne Stelle, weil es dort schlicht keine eigene Adresse je Ausschreibung
gibt — Landeshauptstadt Potsdam (23 von 23), Berlin Partner (2 von 2) und die
Kassenärztliche Bundesvereinigung (4 von 4). Folge: „Im Browser" öffnet die
Liste, und die archivierte Seite ist die Übersicht, nicht die Ausschreibung.
Der Titel und die Eckdaten stimmen trotzdem.

## Ehrliche Grenzen

- **Der schnelle Modus verpasst Stellen mit nichtssagendem Titel.** Wer nichts
  übersehen will, kreuzt „Gründlich suchen" an und nimmt die längere Laufzeit
  in Kauf.
- **Der Stichwort-Filter kann danebenliegen.** Der erste echte Lauf fand 901
  Stellen und behielt 34; davon waren beim Nachsehen 12 Fehltreffer
  (Bürosachbearbeitung, Anwendungsentwicklung, Ingenieurstellen in der
  Versorgungstechnik, ein Crossmedia-Redakteur). Alle sind jetzt ausgeschlossen,
  aber Randfälle bleiben möglich. Dafür gibt es den 🗑-Knopf, die Stichwortlisten
  oben in `einordnung.py` und `suche.py --nachfiltern`.
- **Gendersonderzeichen werden vor dem Vergleich entfernt** (`vergleichsform()`),
  damit „Mitarbeiter:in", „Mitarbeiter*in" und „Mitarbeiterin" dieselbe Form
  ergeben. Vorher griff ein Stichwort nur in der Schreibweise, in der es
  zufällig notiert war — „Wissenschaftliche:r Mitarbeiter:in" rutschte so durch
  den Ausschluss.
- **Die Passungs-Punkte sind eine Sortierhilfe, kein Urteil.** Sie kennen weder
  den Zuschnitt der Stelle noch das Team.
- **Angaben sind aus der Ausschreibung übernommen, ohne Gewähr.** Vor jeder
  Bewerbung auf der Seite des Arbeitgebers nachsehen — besonders die Frist.
- **Das Karriereportal Berlin** wird derzeit wie eine normale Arbeitgeberseite
  gelesen (16 Treffer). Es hat wie Interamt eine eigene Suche mit Filtern; die
  ist noch nicht erschlossen, da ließe sich mehr holen.
- **Das Bewerberportal der Landeshauptstadt Potsdam** (GWT-Anwendung) stellte
  sich schon dem Vorläufer in den Weg. Es steht im Register als `tief` markiert,
  ob Scrapling/Patchright damit zurechtkommt, zeigt erst der Betrieb.
- **16 der 93 Arbeitgeberseiten** zeigten beim Prüflauf keine Stellen. Das ist
  meist kein Fehler, sondern heißt schlicht: dort ist gerade nichts offen.

## Dateien

| Datei | Zweck |
|---|---|
| `einordnung.py` | Berufsfelder, Ausschlüsse, Eckdaten-Erkennung, Passungs-Punkte |
| `arbeitgeber.py` | Register der 93 Arbeitgeber, dazu die nicht aufgenommenen |
| `quelle_interamt.py` | Interamt-Umkreissuche und Detailabruf |
| `quelle_berlin.py` | Karriereportal Berlin, blättert über die Adresse |
| `holen.py` | Scrapling-Abrufschicht und Link-Erkennung |
| `suche.py` | Suchsteuerung, führt die Quellen zusammen |
| `datenbank.py` | SQLite, Triage-Status, Kennzahlen fürs Dashboard |
| `steckbrief.py` | PDF je Stelle und Dossier |
| `pruefe_arbeitgeber.py` | prüft alle Karriereseiten |
| `finde_karriereseite.py` | sucht die echte Karriereseite eines Arbeitgebers |
| `erkunde_portale.py` | untersucht Portale auf ihre Schnittstellen |
| `stellenradar.py` | die Oberfläche (Dashboard, Listen, Triage) |
| `INSTALLIEREN.bat` | einmalige Einrichtung auf einem neuen Rechner |
| `PRUEFEN.bat` | Zustandsbericht |
| `KI_NACHINSTALLIEREN.bat` · `BROWSER_NACHINSTALLIEREN.bat` | Nachinstallation |
| `_setup\` | die Installationsskripte und der Python-Installer |
| `LIESMICH.txt` | Kurzanleitung für die Bedienung |
| `Stellenradar_starten.bat` | Starter, wird vom Desktop-Symbol aufgerufen |
| `Verknuepfung_auf_Desktop_anlegen.bat` | legt das Symbol an |
| `oberflaeche.py` | Bausteine der Oberfläche: Farben, Karten, Marken, Knöpfe |
| `konfiguration.py` | Standardwerte für Berufsfelder, Gewichtung und Profil |
| `archiv.py` | sichert die Ausschreibungsseiten als PDF |
| `ki.py` | Anbindung an Ollama samt Härtungen |
| `briefing.py` | baut das Vorbereitungs-Briefing je Favorit |
| `erfassen.py` | Stellen von Hand aufnehmen, per Link oder Text |
| `sicherungen\` | Tageskopien der Datenbank, die letzten sieben |
| `berufsfelder.json` | entsteht, sobald ein Berufsfeld geändert wurde |
| `gewichtung.json` | entsteht, sobald die Gewichtung geändert wurde |
| `profil.json` | entsteht, sobald das Profil geändert wurde |
| `stellenradar.db` | die Stellen samt Status, Notizen und PDF-Pfaden |
| `archiv\` | die gesicherten Originalseiten |
| `fehler.log` | entsteht nur, wenn das Programm nicht starten konnte |
| `lauf.log` | Protokollzeilen des Suchlaufs (entsteht beim Start ohne Konsole) |
| `steckbriefe\` | die erzeugten PDFs |
