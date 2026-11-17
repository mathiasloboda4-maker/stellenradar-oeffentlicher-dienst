# Stellenradar — Projektdokumentation und Übergabe

**Für alle, die das Programm bedienen, anpassen oder weiterentwickeln —
Menschen wie KI-Assistenten.**

Dieses Dokument enthält alles, was man braucht, um das Programm zu verstehen,
zu bedienen, zu erweitern und zu reparieren. Es ist bewusst ausführlich: Wer
hier liest, hat die Entstehung nicht miterlebt.

Stand: 13.11.2026 · Entstanden zwischen dem 11. und 13.11.2026

---

## Inhalt

1. [Worum es geht](#1-worum-es-geht)
2. [In fünf Minuten startklar](#2-in-fünf-minuten-startklar)
3. [Wie das Programm aufgebaut ist](#3-wie-das-programm-aufgebaut-ist)
4. [Die Datenquellen](#4-die-datenquellen)
5. [Die Einordnung: Was gefunden wird und warum](#5-die-einordnung-was-gefunden-wird-und-warum)
6. [Die Datenbank](#6-die-datenbank)
7. [Die Oberfläche](#7-die-oberfläche)
8. [Die lokale KI](#8-die-lokale-ki)
9. [PDF: Steckbriefe, Archiv, Dossier](#9-pdf-steckbriefe-archiv-dossier)
10. [Stolperfallen — bitte vor dem Ändern lesen](#10-stolperfallen--bitte-vor-dem-ändern-lesen)
11. [Testen](#11-testen)
12. [Wartung](#12-wartung)
13. [Gemessene Werte](#13-gemessene-werte)
14. [Was offen ist](#14-was-offen-ist)
15. [Wenn du etwas ändern willst](#15-wenn-du-etwas-ändern-willst)

---

## 1. Worum es geht

Der Stellenradar sucht Stellenausschreibungen, die zu **einem hinterlegten
Profil** passen, und macht daraus eine überschaubare Arbeitsliste.

**Das Profil** steuert alle Entscheidungen im Programm. Es steht nicht im
Code, sondern in drei JSON-Dateien neben dem Programm, die im Fenster gepflegt
werden:

| Datei | Inhalt | Im Fenster unter |
|---|---|---|
| `profil.json` | Name, Abschluss, Wohnort, Werdegang, Stärken, Weiterbildungen | Berufsfelder |
| `berufsfelder.json` | je Berufsfeld die eigenen Kompetenzen — Belege aus dem Lebenslauf | Berufsfelder |
| `gewichtung.json` | wie viele Punkte wofür vergeben werden | Gewichtung |

Fehlt eine Datei, gilt ein neutrales Beispiel aus `konfiguration.py`. **Beim
ersten Start also zuerst das eigene Profil eintragen** — sonst sortiert das
Programm nach fremden Maßstäben, und das KI-Briefing hat keine Belege, die es
den Anforderungen gegenüberstellen könnte.

**Der Suchraum**: öffentlicher Dienst in Brandenburg und Berlin, Bund mit Sitz
Berlin, Wissenschaftseinrichtungen und **Beratungshäuser, die für die
öffentliche Hand arbeiten** (PD, INFORA, init, Cassini, msg, Materna,
BearingPoint …). Geografisch Potsdam, Berlin und das Umland.

**Sechs Berufsfelder** als Auslieferungsstand. Sie sind ein Beispiel für ein
Profil im Umfeld Verwaltungsdigitalisierung und vollständig austauschbar — im
Fenster unter „Berufsfelder", ohne eine Zeile Code:

| | Feld |
|---|---|
| ① | Digitalisierung & E-Government |
| ② | IT-Produkt- & Anforderungsmanagement |
| ③ | Projektleitung / PMO |
| ④ | Prozess- & Changemanagement |
| ⑤ | Kunden- & Servicemanagement |
| ⑥ | Wissenschafts- & Fördermanagement |

**Die Grundregel des Filters**: Kein Treffer in einem Berufsfeld heißt
verworfen. Lieber eine passende Stelle übersehen als eine Liste, die man nicht
mehr durchsieht. Ein echter Lauf prüfte 901 Stellen und behielt 34.

**Vorgeschichte**: Der Vorläufer arbeitete mit `requests`, BeautifulSoup und
Playwright und scheiterte an mehreren Portalen — insbesondere an solchen, die
ihre Trefferliste erst per JavaScript aufbauen. Der Stellenradar ist eine
Neuschreibung auf Scrapling, kein Umbau. Was aus dem Vorläufer übernommen
wurde, sind die teuer erkauften Erfahrungen: die Portal-Eigenheiten in
Abschnitt 4 und die drei Härtungen der KI-Anbindung in Abschnitt 8.

---

## 2. In fünf Minuten startklar

### Programm benutzen

Desktop-Symbol **Stellenradar**, oder `Stellenradar_starten.bat`.

### Am Programm arbeiten

Es gibt eine eigene Python-Umgebung im Projektordner. **Immer diese benutzen**,
nie das globale Python:

```bash
.venv\Scripts\python.exe stellenradar.py
```

Mit `python.exe` statt `pythonw.exe` erscheinen Fehlermeldungen im Fenster —
beim normalen Start über das Symbol sind sie unsichtbar.

### Die wichtigsten Befehle

```bash
.venv\Scripts\python.exe stellenradar.py --selftest
```
```bash
.venv\Scripts\python.exe stellenradar.py --guitest
```
```bash
.venv\Scripts\python.exe suche.py --runden 25
```
```bash
.venv\Scripts\python.exe suche.py --nachfiltern
```
```bash
.venv\Scripts\python.exe suche.py --eckdaten-neu
```
```bash
.venv\Scripts\python.exe suche.py --punkte-neu
```
```bash
.venv\Scripts\python.exe pruefe_arbeitgeber.py
```

**Nach jeder Änderung am Code: beide Tests laufen lassen.** Sie sind schnell
und fangen das meiste ab.

### Wo was liegt

| Pfad | Inhalt |
|---|---|
| `stellenradar.db` | alle Stellen samt Triage, Notizen, Favoriten, Briefings |
| `archiv\` | PDF-Kopien der Ausschreibungsseiten |
| `steckbriefe\` | aufbereitete PDF je Stelle, dazu das Dossier |
| `sicherungen\` | Tageskopien der Datenbank, die letzten sieben |
| `berufsfelder.json` | entsteht erst, wenn ein Berufsfeld geändert wurde |
| `gewichtung.json` | entsteht erst, wenn die Gewichtung geändert wurde |
| `profil.json` | entsteht erst, wenn das Profil geändert wurde |
| `fehler.log` | entsteht nur, wenn das Programm nicht starten konnte |
| `lauf.log` | Protokollzeilen beim Start ohne Konsole |

---

## 3. Wie das Programm aufgebaut ist

18 Python-Dateien, rund 7.800 Zeilen. Keine Klassenhierarchien, keine
Frameworks — flache Module mit klarer Zuständigkeit.

### Datenfluss eines Suchlaufs

```
  quelle_interamt.py ─┐
  quelle_berlin.py   ─┼─→ suche.Lauf ─→ einordnung.einordnen ─→ datenbank.speichern
  holen.py (93 Seiten)┘        │                                        │
                               │                                        ↓
                               └──────────────────────────→ archiv.stelle_archivieren
```

### Die Module

| Datei | Zeilen | Zuständig für |
|---|---:|---|
| `stellenradar.py` | 2649 | Oberfläche: Fenster, neun Ansichten, Dialoge, Hintergrundarbeiten |
| `einordnung.py` | 657 | **Herzstück.** Berufsfelder, Ausschlüsse, Eckdaten-Erkennung, Punkte |
| `datenbank.py` | 514 | SQLite: Schema, Migration, Triage, Kennzahlen, Sicherung |
| `steckbrief.py` | 474 | PDF je Stelle und das Dossier |
| `suche.py` | 428 | Suchsteuerung: führt die Quellen zusammen, Nachbesserungen |
| `quelle_interamt.py` | 375 | Interamt-Umkreissuche und Detailabruf |
| `konfiguration.py` | 332 | Standardwerte und JSON-Verwaltung für Felder, Gewichte, Profil |
| `briefing.py` | 320 | Vorbereitungs-Briefing je Favorit |
| `oberflaeche.py` | 297 | Farben, Karten mit runden Ecken, Marken, Knöpfe |
| `arbeitgeber.py` | 249 | Register der 93 Arbeitgeberseiten |
| `holen.py` | 242 | Abrufschicht über Scrapling, Link-Erkennung |
| `finde_karriereseite.py` | 205 | **Werkzeug**: sucht die echte Karriereseite eines Arbeitgebers |
| `archiv.py` | 188 | sichert Ausschreibungsseiten als PDF |
| `ki.py` | 185 | Ollama-Anbindung samt Härtungen |
| `quelle_berlin.py` | 181 | Karriereportal Berlin |
| `erfassen.py` | 173 | Stellen von Hand aufnehmen |
| `pruefe_arbeitgeber.py` | 169 | **Werkzeug**: prüft alle Karriereseiten |
| `erkunde_portale.py` | 127 | **Werkzeug**: untersucht ein Portal auf seine Schnittstellen |

Die drei als **Werkzeug** markierten Dateien gehören nicht zum laufenden
Programm. Sie dienen der Wartung (siehe [Abschnitt 12](#12-wartung)).

### Abhängigkeiten

```
scrapling[fetchers]>=0.5.1   Abruf und Auslesen von Webseiten
pypdf                        PDF-Metadaten
pymupdf                      PDF prüfen und Seiten als Bild rendern
```

Dazu Tkinter und sqlite3 aus der Standardbibliothek, Chrome oder Edge für die
PDF-Erzeugung und optional Ollama für die KI.

**Warum eine eigene `.venv`**: Die globalen Python-Pakete auf Mathias' Rechner
sind durch den MSIX-Container der Claude-App zweigeteilt — was dort installiert
wurde, sehen Programme außerhalb nicht. Eine Umgebung im Projektordner ist von
beiden Seiten gleich sichtbar.

---

## 4. Die Datenquellen

Drei Arten, zusammengeführt in `suche.Lauf.starten()`.

### 4.1 Interamt — die wichtigste Einzelquelle

`quelle_interamt.py` · [interamt.de](https://www.interamt.de)

Das gemeinsame Stellenportal des öffentlichen Dienstes. Eine **Umkreissuche um
PLZ 14467 (Potsdam)** erfasst Berlin, Potsdam und Umgebung in einem Durchgang:
**828 Stellen** am 11.11.2026. Die Trefferliste liefert pro Stelle schon
Behörde, Bezeichnung, Besoldung, Entgelt, PLZ/Ort, **Entfernung in km**,
Dienstort, Einstelldatum und **Bewerbungsfrist**.

Drei Eigenheiten bestimmen den Code. Alle wurden am lebenden Portal ermittelt,
keine davon ist dokumentiert:

1. **Apache-Wicket-Anwendung.** Der Suchknopf lässt sich nicht zuverlässig
   anklicken. **Enter im PLZ-Feld** schickt die Suche ab.
2. **Die Liste blättert nicht, sie lädt nach.** Der Knopf „mehr laden" hängt
   je Klick **10 Zeilen** an. Im DOM stehen 20 `tbody tr`, aber nur 10 sind
   Datenzeilen mit zehn Zellen — die übrigen gehören zu einer zweiten Tabelle
   auf derselben Seite. Wer `tbody tr` zählt, zählt doppelt.
3. **Der Cookie-Hinweis klebt am Seitenende und verdeckt genau diesen Knopf.**
   Ohne Schließen läuft jeder Klick in eine Zeitüberschreitung. Deshalb wird
   das Banner **vor und nach** der Suche geschlossen, und `_mehr_laden()` ist
   selbstheilend: Bei einem Fehlschlag schließt es das Banner und versucht es
   noch einmal.

Interamt schreibt selbst, dass es ausschließlich notwendige Cookies setzt — es
gibt also nichts abzulehnen, Bestätigen ist hier die datensparsame Antwort.

**Detailseiten** haben eine feste Adresse (`…/koop/app/stelle?id=NUMMER`) und
lassen sich **ohne Browser** abrufen. Deshalb: Liste einmal im Browser,
Details über HTTP.

**Abdeckung**: Der Standardwert von 25 Nachladerunden liest etwa 260 der 828
Stellen. Für den laufenden Betrieb genügt das, weil die Liste nach
Einstelldatum absteigend sortiert ist und Neues oben steht. **Für den ersten
Lauf 85 Runden einstellen** — das liest den gesamten Bestand.

### 4.2 Karriereportal Berlin

`quelle_berlin.py` · [karriereportal-stellen.berlin.de](https://www.karriereportal-stellen.berlin.de)

Bündelt Senatsverwaltungen, die zwölf Bezirksämter, Polizei, Feuerwehr und die
nachgeordneten Behörden: **629 Stellen** am 12.11.2026.

**Warum eine eigene Quelle?** Als eine von 93 Karriereseiten behandelt lieferte
das Portal **genau einen Treffer**, weil die Übersicht nur die ersten rund 15
Stellen zeigt. Es blättert aber über einen schlichten Parameter in der Adresse
(`?start=0`, `?start=20`, …) und braucht dafür **keinen Browser**. Als eigene
Quelle gelesen: 526 Stellen geprüft, 8 passende gefunden.

Die ausschreibende Behörde steht **nicht** in der Übersicht, wohl aber im
Detailtext — `arbeitgeber_finden()` zieht sie heraus. Ohne das stünde bei allen
600 Stellen nur „Land Berlin".

### 4.3 Die 93 Arbeitgeberseiten

`arbeitgeber.py` + `holen.py`

| Gruppe | Anzahl |
|---|---:|
| Öffentlicher Dienst Brandenburg | 35 |
| Wissenschaft Potsdam | 11 |
| Öffentlicher Dienst Berlin | 16 |
| Wissenschaft Berlin | 8 |
| Bund | 6 |
| Public-Sector-Beratung | 17 |

Jeder Eintrag trägt `sektor`, `region`, `ort`, `gruppe` und das Kennzeichen
`tief` (= Seite braucht einen Browser).

**Die Karriereseiten wurden nicht geraten.** 123 Kandidaten wurden geprüft, 93
aufgenommen. Wo eine geratene Adresse ins Leere lief, hat
`finde_karriereseite.py` die echte gesucht: Startseite holen, Links nach
Karriere-Signalwörtern bewerten, die besten Kandidaten wirklich abrufen und
prüfen, ob dort Ausschreibungen stehen.

**20 Arbeitgeber sind bewusst draußen**, jeweils mit Begründung in
`arbeitgeber.NICHT_AUFGENOMMEN`. Kurz: Capgemini, Accenture, Deloitte, KPMG,
Kienbaum, adesso, T-Systems und IBM haben ihre Stellensuche hinter
JavaScript-Portalen ohne feste Adresse; BVG, BSR und die Sparkassen haben keine
auffindbare Stellenübersicht; die meisten Bundesministerien schreiben ohnehin
über Interamt aus.

### 4.4 Die Abrufschicht

`holen.py` nutzt Scrapling in zwei Stufen:

| Weg | Wofür |
|---|---|
| `Fetcher` | normale Seiten, ohne Browser, schnell — **Standard** |
| `StealthyFetcher` | Seiten, deren Inhalt erst per JavaScript entsteht |

Kommt über HTTP zu wenig Text an (unter 1200 Zeichen), wird automatisch auf den
Browser hochgeschaltet. Das Kennzeichen `tief` im Register spart diesen Umweg,
wo er bekanntermaßen nötig ist.

**Link-Erkennung** (`stellen_links`): Das Geschlechtskürzel im Linktext ist das
stärkste Signal; sonst zählt eine detailseiten-typische URL plus ein
brauchbarer Titel. Steht im Link nur „mehr erfahren", sucht
`_titel_aus_umgebung()` die Überschrift in der umgebenden Karte.

**Rückfall** (`seiten_titel_stellen`): Listet eine Seite ihre Ausschreibungen
ohne eigene Links auf, werden Zeilen mit Geschlechtskürzel als Stellen
gewertet und die Übersichtsseite als Adresse verwendet. Diese Treffer tragen
`aus_liste=True`.

**Rücksicht**: erkennbare Browserkennung, 0,8 s Pause je Arbeitgeber, 0,45 s je
Detailseite, höchstens 25 Treffer je Arbeitgeber und Lauf. Anti-Bot-Umgehung
und CAPTCHA-Lösen werden bewusst nicht genutzt.

---

## 5. Die Einordnung: Was gefunden wird und warum

`einordnung.py` — wer hier etwas ändert, ändert, was das Programm findet.

### Ablauf je Kandidat

```
Titel ──→ ist_ausgeschlossen()  ──→ raus (harter Ausschluss, hat Vorrang)
      ──→ felder_bestimmen()    ──→ raus, wenn kein Feld trifft
      ──→ Volltext holen
      ──→ Eckdaten herausziehen (Frist, Entgelt, Kontakt …)
      ──→ punkte_berechnen()
      ──→ speichern
```

### Berufsfelder und Stichworte

Stehen **nicht mehr im Code**, sondern in `konfiguration.STANDARD_FELDER` bzw.
in `berufsfelder.json`. Im Programm unter **Berufsfelder** bearbeitbar.
`einordnung.neu_laden()` zieht Änderungen sofort nach.

Stichworte sind nach Gewicht gruppiert:

| Gewicht | Bedeutung | Beispiel |
|---|---|---|
| 3 | sehr aussagekräftig | `e-government`, `anforderungsmanag` |
| 2 | deutlich | `digitalisierung`, `qualitätsmanag` |
| 1 | schwaches Signal | `stabsstelle`, `business analyst` |

Wortstämme genügen: `projektleit` findet Projektleiterin und Projektleitung.
Das Gewicht geht in die Punkte ein, nicht nur in die Zuordnung. **Der Titel
wiegt doppelt** — eine Stelle, deren Feld nur im Fließtext auftaucht, ist
meist keine Stelle in diesem Feld.

### Harte Ausschlüsse

`einordnung.AUSSCHLUSS`, 222 Begriffe. Sie haben **immer** Vorrang.
Gruppen: Studierende und Einstieg, Pflege/Medizin/Therapie, Soziales und
Pädagogik, rein wissenschaftliche Qualifikationsstellen, Küche/Reinigung/
Handwerk/Fahrdienste, Sekretariat/Empfang/Sicherheit, rein juristische Stellen,
reine Softwareentwicklung und Administration, Vollzugsdienste, Bau- und
Technikgewerke.

Die Liste ist gewachsen, weil Fehltreffer auftraten. Jeder Nachtrag steht im
Code mit Begründung, etwa:

```python
# Nachgezogen nach dem ersten Probelauf am 11.11.2026: Diese Stellen hatten
# ein passendes Schlagwort im Titel ("Projektleitung", "Koordination"), aber
# ein Sachgebiet, das mit dem Profil nichts zu tun hat.
"kinderschutz", "verfahrenstechnik", "baumaßnahme", …
```

**Gendersonderzeichen werden vor jedem Vergleich entfernt**
(`vergleichsform()`), damit „Mitarbeiter:in", „Mitarbeiter*in" und
„Mitarbeiterin" dieselbe Form ergeben. Ohne das griff ein Stichwort nur in der
Schreibweise, in der es zufällig notiert war.

### Eckdaten-Erkennung

| Funktion | Zieht heraus |
|---|---|
| `frist_finden` | Bewerbungsfrist als ISO-Datum |
| `eintritt_finden` | Eintrittstermin, auch „nächstmöglich" |
| `entgelt_finden` | E/A/B-Gruppe, geprüft gegen `HOECHSTE_GRUPPE` |
| `umfang_finden` | Vollzeit / Teilzeit |
| `befristung_finden` | befristet / unbefristet |
| `kontakt_finden` | Ansprechperson **mit Anrede** |
| `telefon_finden`, `email_finden`, `ort_finden` | ebendas |

### Passungs-Punkte

`punkte_berechnen(daten, gewichte)` — sortiert die Liste, ersetzt kein Urteil.
Jede Stelle trägt ihre Begründung mit:

```
Berufsfeld-Treffer: +7 | passt auf mehrere Berufsfelder: +2 |
Region Potsdam: +5 | Öffentlicher Dienst Brandenburg: +4 |
E 13: +4 | unbefristet: +3 | Frist angegeben: +1
```

**Alle Gewichte sind einstellbar** (`gewichtung.json`, Ansicht „Gewichtung").
Vier Schnellvorlagen setzen eine Grundhaltung: Nähe, Bezahlung, fachliche
Passung, ausgewogen. Nach dem Speichern werden alle gespeicherten Stellen neu
bewertet (`suche.punkte_neu()`).

---

## 6. Die Datenbank

SQLite, `stellenradar.db`, zwei Tabellen.

### `stellen` — 36 Spalten

| Gruppe | Spalten |
|---|---|
| Kennung | `id`, `url` (eindeutig), `quelle`, `manuell` |
| Stelle | `titel`, `arbeitgeber`, `sektor`, `region`, `ort`, `entfernung_km` |
| Einordnung | `felder` (JSON), `feld_haupt`, `punkte`, `punkte_gruende` |
| Eckdaten | `frist`, `eintritt`, `entgelt`, `umfang`, `befristung` |
| Kontakt | `kontakt`, `telefon`, `email` |
| Inhalt | `volltext`, `pdf_pfad`, `archiv_pdf` |
| Zeit | `gefunden_am`, `geprueft_am` |
| Triage | `status`, `notiz`, `favorit` |
| Briefing | `briefing`, `briefing_am`, `briefing_modell` |
| Verlauf | `beworben_am`, `rueckmeldung`, `wiedervorlage` |

### Das Status-Modell

```
   neu  ──⭐──→  vorgemerkt  ──✉──→  beworben
    │                │                  │
    └────🗑──────────┴──────────────────┘
                     ↓
                 verworfen  ──↩──→  neu
```

| Status | Bedeutung |
|---|---|
| `neu` | frisch gefunden, noch nicht angesehen |
| `vorgemerkt` | interessant, kommt ins Dossier |
| `beworben` | Bewerbung ist raus |
| `verworfen` | **kommt nie wieder** |

**Verworfen ist mehr als „ausgeblendet".** `kennt_url()` wird vor dem Abruf
einer Detailseite gefragt — eine verworfene Stelle wird gar nicht erst neu
geladen. Ohne das sortiert man dieselbe Stelle jede Woche erneut aus.

**Beim Verwerfen werden die Dokumente gelöscht** (`dokumente_loeschen`):
Steckbrief, Seitenkopie und Briefing. Sonst wächst der Ordner mit Unterlagen
zu Stellen voll, die nie infrage kamen. Holt man eine Stelle zurück, steht sie
ohne Dokumente da — die Originalseite ist dann vielleicht schon offline.

**Favorit ist kein Status, sondern ein eigenes Merkmal.** Eine beworbene Stelle
darf gleichzeitig Favorit sein.

### Auffrischen statt Überschreiben

Findet ein Lauf eine bekannte Stelle wieder, werden nur die Sachangaben
aktualisiert. **Status, Notiz, Fundtag und die erzeugten PDFs bleiben** — das
ist Arbeit, die nicht verloren gehen darf.

### Migration

Neue Spalten kommen in `NACHGEREICHTE_SPALTEN`. `einrichten()` prüft bei jedem
Start `PRAGMA table_info` und ergänzt fehlende per `ALTER TABLE`. So wächst
eine bestehende Datenbank mit, ohne dass jemand sie neu anlegen muss.

### Sicherung

`sichern()` legt beim Programmstart eine Tageskopie unter `sicherungen\` an
und hebt die letzten sieben auf. Verwendet `sqlite3.Connection.backup()`, nicht
eine Dateikopie — das ist auch dann konsistent, wenn gerade geschrieben wird.

---

## 7. Die Oberfläche

`stellenradar.py` (Logik) + `oberflaeche.py` (Bausteine). Tkinter, Thema
„clam".

### Aufbau

```
┌─────────────────────────────────────────────────┐
│ Kopfzeile: Titel · Suchlauf · Stopp · Erfassen  │
│            Dossier · Zahnrad                    │
├──────────┬──────────────────────────────────────┤
│ Seiten-  │  Inhaltsbereich (hell, weiße Karten) │
│ leiste   │                                      │
│ (navy)   │                                      │
├──────────┴──────────────────────────────────────┤
│ Fußzeile: Fortschritt (nur bei Bedarf) · Status │
└─────────────────────────────────────────────────┘
```

### Die neun Ansichten

| Schlüssel | Klasse | Inhalt |
|---|---|---|
| `dashboard` | `DashboardAnsicht` | Handlungsbedarf, Kennzahlen, Fristen-Ampel, Verteilung |
| `neu`, `vorgemerkt`, `beworben`, `verworfen` | `ListenAnsicht` | Stellenlisten mit Filter und Vorschau |
| `favoriten` | `FavoritenAnsicht` | Durchschalten links, Briefing rechts |
| `berufsfelder` | `BerufsfelderAnsicht` | Felder, Stichworte, Kompetenzen, Profil |
| `gewichtung` | `GewichtungAnsicht` | Punkte einstellen |
| `archiv` | `ArchivAnsicht` | gesicherte Seiten |

Alle werden beim Start angelegt und per `pack_forget()` / `pack()` getauscht.
`App.zeigen(schluessel)` ruft dabei `ansicht.laden()` auf — **jede Ansicht baut
ihren Inhalt bei jedem Aufruf neu**. Das ist absichtlich einfach gehalten.

### Die Farbwelt

Bewusst **nicht** das Hochschul-CI, mit dem Mathias sonst arbeitet — das sind
private Bewerbungsunterlagen. Palette in `oberflaeche.py`: helle Fläche
`#F4F7FC`, weiße Karten, dunkle Seitenleiste `#1E2749`, Indigo `#5B63E8`,
Mint `#10B981`, Gelb `#F59E0B`, Koralle `#F2663C`, Rot `#E5484D`.

### `Karte` — runde Ecken in Tkinter

Tkinter kann das nicht von Haus aus. Die Klasse legt eine Leinwand per
`place()` über die ganze Fläche und zeichnet dort ein `create_polygon(…,
smooth=True)`. Der Inhalt sitzt in `.innen` und wird eingerückt.

**Das Polster muss mindestens so groß sein wie der Eckradius**, sonst decken
die eckigen Inhaltsflächen die runden Ecken wieder zu.

### Hintergrundarbeiten

Alles Langsame läuft im Nebenthread und meldet sich über
`self.warteschlange` zurück; `_warteschlange_pruefen()` liest sie im
Hauptthread per `after()`. **Tkinter direkt aus einem fremden Thread
anzusprechen ist nicht verlässlich** — das hat im Vorläuferprojekt schon einen
Absturz verursacht.

Nachrichtenarten: `hinweis`, `fortschritt`, `lauf_fertig`, `pdf_fertig`,
`archiv_fertig`, `dossier_fertig`, `dossier_fehler`, `briefing_fertig`,
`punkte_fertig`, `nachfilter_fertig`.

---

## 8. Die lokale KI

`ki.py` + `briefing.py` · Ollama, läuft auf dem eigenen Rechner. **Es verlässt
nichts das Gerät.**

### Modellwahl

`ki.BEVORZUGT` = `gemma4:12b` → `qwen3.5:9b` → `qwen3.5:2b`. `bestes_modell()`
nimmt das erste vorhandene. `starten()` fährt den Dienst hoch, wenn er nicht
läuft.

Der Installer wählt nach Arbeitsspeicher: ab 16 GB `gemma4:12b`, 12–16 GB
`qwen3.5:9b`, 8–12 GB `qwen3.5:2b`, darunter keines. **Auf einem Gerät mit
8 GB** läuft also das kleine Modell: mehrere Minuten je Kurzinfo, einfachere
Formulierung. Das Programm funktioniert vollständig auch ohne KI — die
Favoriten zeigen dann die Eckdaten ohne Einschätzung.

### Drei Härtungen aus dem Vorläuferprojekt

1. **`gemma4:12b` ist ein Reasoning-Modell und liefert leeren Inhalt**, wenn
   man `think` nicht ausdrücklich abschaltet.
2. **Ein zu kleines `num_ctx` schneidet den Prompt stillschweigend vorne ab** —
   also genau dort, wo Werdegang und Kompetenzen stehen. Deshalb 16384.
3. **Kleine Modelle erfinden Fakten.** Im Vorläufer schrieb eines dem Profil
   eine „fünfjährige Erfahrung in leitenden Positionen" zu, die nirgends
   hinterlegt war. Deshalb bekommt die KI
   alles Prüfbare vorgegeben und wird per Systemtext an Ausschreibungstext und
   Profil gebunden. `aufraeumen()` entfernt Denkprozess und Markdown aus der
   Antwort.

### Der Aufbau des Briefings

**Die Trennung ist der Kern dieses Entwurfs:**

| | Abschnitt | Woher |
|---|---|---|
| ① | Key Facts zur Stelle | **Datenbank**, nicht KI |
| ② | Ansprechpartner | **Datenbank**, nicht KI |
| ③ | Meine hinterlegten Kompetenzen | **Konfiguration**, nicht KI |
| ④ | Was die Stelle verlangt | KI, streng am Ausschreibungstext |
| ⑤ | Wo meine Kompetenzen passen | KI, als „Anforderung → Beleg" |
| ⑥ | Der Elefant im Raum | KI: Lücken benennen und drehen |
| ⑦ | Zum Arbeitgeber | KI aus Allgemeinwissen — **als ungeprüft gekennzeichnet** |
| ⑧ | Fragen fürs Gespräch | KI |

① bis ③ stimmen, weil sie nicht von der KI stammen. Ein Hinweis am Ende des
Dokuments sagt das noch einmal ausdrücklich.

`abschnitte_formatieren()` normiert die Überschriften — die Modelle schreiben
sie nicht immer sauber ab (im Versuch kam „ZUM ARBITGEBER" zurück).

---

## 9. PDF: Steckbriefe, Archiv, Dossier

| Was | Modul | Inhalt |
|---|---|---|
| **Steckbrief** | `steckbrief.py` | Eckdaten, Punkte-Begründung, Notiz, **vollständiger Ausschreibungstext** |
| **Archiv** | `archiv.py` | die Originalseite, wie sie im Browser aussieht |
| **Dossier** | `steckbrief.py` | alle vorgemerkten Stellen in einem Dokument, Fristenübersicht vorneweg |

**Warum das Archiv?** Portale nehmen Ausschreibungen nach Fristende offline,
oft ohne Vorwarnung. Danach ist nicht mehr nachvollziehbar, worauf man sich
beworben hat. Es läuft automatisch nach jedem Suchlauf, 7 bis 10 Sekunden und
0,2 bis 1 MB je Seite.

**Erzeugung**: HTML → Chrome headless (`--headless=new --print-to-pdf`) →
`pypdf` für die Metadaten. Das Archiv druckt direkt von der URL.

---

## 10. Stolperfallen — bitte vor dem Ändern lesen

Jede dieser Fallen hat real Zeit gekostet. Sie stehen auch als Kommentar an
der jeweiligen Stelle im Code.

### Python und Tkinter

**`pythonw.exe` hat kein `sys.stdout`.**
Beim Start ohne Konsole ist `sys.stdout` `None`. Ein
`sys.stdout.reconfigure(...)` stirbt dort sofort und **wortlos** — das Fenster
erscheint gar nicht erst. Irreführend: Aus einer Shell gestartet erbt
`pythonw` ein stdout und läuft. `_stdout_vorbereiten()` leitet beide Ströme
notfalls nach `lauf.log` um. Das ist nicht kosmetisch: Scrapling schreibt
beim Suchlauf Protokollzeilen nach stdout — ohne Ziel bräche der Lauf ab.

**`tk.Text` fordert 80 Zeichen Breite an.**
Stehen mehrere nebeneinander, bekommt das erste alles und die übrigen werden
aus dem Fenster gedrängt. `width=1` setzen und die Breite über `fill`/`expand`
verteilen lassen (`oberflaeche.textfeld`).

**`pack` gibt dem zuletzt gepackten Element nur den Rest.**
Ein `side="right"`-Knopf wird abgeschnitten, wenn er nach den linken gepackt
wird. **Rechte Knöpfe zuerst packen.**

**Fußzeilen zuerst packen.**
Widgets mit `side="bottom"` müssen vor dem expandierenden Hauptbereich
gepackt werden, sonst werden sie aus dem Fenster gedrückt.

**Ein leerer `ttk.Progressbar` sieht aus wie ein defekter Rollbalken.**
Deshalb wird er nur gepackt, solange etwas läuft.

### Reguläre Ausdrücke

**`re.IGNORECASE` macht auch `[A-ZÄÖÜ]` unwirksam.**
Aus „Frau Dr. Katrin Mueller" wurde so „Frau Dr", weil jedes klein
geschriebene Wort als Name durchging. Lösung: den Schalter mit `(?i:…)` auf
die Signalwörter begrenzen, den Namensteil groß/klein-empfindlich lassen.

**Zeilenumbrüche zwischen Beschriftung und Wert.**
`FRIST_RE` verbot sie (`[^\n\d]`). In Tabellen-Layouts steht aber genau das:

```
Bewerbungsfrist:
26.11.2026
```

Jetzt erlaubt `_FRIST_LUECKE` einfache Umbrüche; eine Leerzeile beendet die
Suche, sonst griffe das Muster über den halben Text.

**Gendersonderzeichen vor dem Vergleich entfernen.**
Sonst greift ein Stichwort nur in der Schreibweise, in der es notiert wurde.
`vergleichsform()` macht aus `:`, `*` und `_` im Wortinneren nichts.

**Entgeltgruppen gegen eine Obergrenze prüfen.**
Ohne das wird aus einer Kennziffer eine Entgeltgruppe — im Probelauf stand
„E 17" in der Liste, das es im TVöD nicht gibt.

### Chrome und PDF

**Chrome braucht eine ausdrückliche `file:///`-Adresse mit Schrägstrichen.**

**Bei einem Leerzeichen im Zielpfad schreibt Chrome stillschweigend nichts.**
Windows-Benutzerordner enthalten fast immer eines. Deshalb wird immer in
einem Temp-Ordner gerendert (dort gilt der 8.3-Kurzname ohne Leerzeichen) und
die fertige Datei danach an ihren Platz kopiert.

### SQLite

**`CREATE INDEX` auf eine Spalte, die die Migration erst anlegt, scheitert.**
Index erst **nach** dem `ALTER TABLE` anlegen.

### PowerShell

**`.ps1`-Dateien mit Umlauten brauchen eine UTF-8-BOM.**
PowerShell 5.1 liest eine Datei ohne BOM als ANSI; die Umlaute zerfallen und
die **Syntax bricht** — das Skript startet gar nicht. Als UTF-8 gelesen war
dieselbe Datei fehlerfrei. Prüfen:

```powershell
[System.Management.Automation.Language.Parser]::ParseFile($pfad,[ref]$null,[ref]$fehler)
```

Schreiben mit `New-Object System.Text.UTF8Encoding $true`.

### Portale

**Das Bewerberportal der Landeshauptstadt Potsdam** (GWT-Anwendung) blieb beim
Vorläufer leer — auch nach 30 Sekunden, auch mit sichtbarem Browser.
Scrapling/Patchright liest es (23 erkannte Ausschreibungen). **Aber** der Link
zeigt auf die Übersicht, weil es dort keine Adresse je Stelle gibt. Dasselbe
bei Berlin Partner und der Kassenärztlichen Bundesvereinigung.

---

## 11. Testen

```bash
.venv\Scripts\python.exe stellenradar.py --selftest
```
Fristen-Fächer, Ampel-Konsistenz, Status-Namen, Wirkung der Gewichtung,
Konfiguration.

```bash
.venv\Scripts\python.exe stellenradar.py --guitest
```
Baut das ganze Fenster mit einer **Wegwerf-Datenbank** auf und prüft: neun
Ansichten, Filter, Triage, Favoriten, Briefing-Grundgerüst, Dokumentenlöschung
beim Verwerfen, Bewerbungsverlauf, Volltextsuche, manuelle Erfassung,
Abgelaufen-Erkennung, Sicherung. Rührt die echten Daten nicht an.

**Beide müssen grün sein, bevor etwas ausgeliefert wird.**

Für Änderungen an der Oberfläche lohnt zusätzlich eine Messung der
Fenstergeometrie — ob alles sichtbar bleibt, sieht man einem Screenshot nicht
immer an. Ein Muster dafür steckt in der Projektgeschichte: Widget-Unterkanten
gegen die Fensterhöhe prüfen.

---

## 12. Wartung

### Eine Karriereseite ist umgezogen

Symptom: Ein Arbeitgeber liefert dauerhaft nichts.

```bash
.venv\Scripts\python.exe pruefe_arbeitgeber.py
```
```bash
.venv\Scripts\python.exe finde_karriereseite.py https://www.beispiel.de
```

Das zweite Werkzeug sucht die echte Karriereseite: Startseite holen, Links
bewerten, Kandidaten wirklich abrufen. Die gefundene Adresse dann in
`arbeitgeber.py` eintragen.

### Ein Portal hat sich geändert

```bash
.venv\Scripts\python.exe erkunde_portale.py interamt
```

Zeichnet den Netzverkehr auf und sucht die Schnittstelle, die die Trefferliste
liefert. So wurden die Eigenheiten von Interamt ermittelt.

### Die Stichwortlisten nachschärfen

Im Programm unter **Berufsfelder** ändern, dann anbieten lassen, die
gespeicherten Stellen neu zu prüfen. Oder von Hand:

```bash
.venv\Scripts\python.exe suche.py --nachfiltern
```

Angefasst wird nur, was auf „neu" steht.

### Die Eckdaten-Erkennung wurde verbessert

```bash
.venv\Scripts\python.exe suche.py --eckdaten-neu
```

Zieht Frist, Entgelt und Kontakt noch einmal aus den gespeicherten Texten.
Sonst profitieren nur neu gefundene Stellen davon.

### Ein neuer Arbeitgeber soll dazu

In `arbeitgeber.py` in die passende Teilliste eintragen:

```python
("Name", "https://…/karriere", "Region", "Ort", False),
```

Das letzte Feld ist `tief` — `True`, wenn die Seite einen Browser braucht.
Danach `pruefe_arbeitgeber.py` laufen lassen.

---

## 13. Gemessene Werte

Damit erkennbar ist, was „normal" aussieht. Alle Zahlen vom 11.–12.11.2026.

### Ein vollständiger Suchlauf

| | |
|---|---|
| Dauer | 9 Minuten (ohne Archivierung) |
| Geprüfte Stellen | 901 |
| Aufgenommen | 34 |
| Nicht passend | 866 |
| Fehler | 0 |

Danach die Archivierung: 21 Seiten, 8,4 MB, keine Fehlschläge.

### Die 93 Arbeitgeberseiten

| Befund | Anzahl |
|---|---:|
| Stellen da, aber kein Berufsfeld getroffen | 57 |
| keine Ausschreibungen erkennbar | 17 |
| liefert passende Stellen | 12 |
| nur profilfremde Stellen | 7 |

Abrufweg: 67 über HTTP, 26 brauchen den Browser.

**Dass 57 Seiten nichts liefern, ist kein Fehler** — die haben Stellen, nur
keine passenden. Der Filter arbeitet.

### Die Portale

| Quelle | Bestand | Davon passend |
|---|---:|---:|
| Interamt (Umkreis 70 km) | 828 | 12 bei 260 gelesenen |
| Karriereportal Berlin | 629 | 8 bei 526 geprüften |

### Qualität der Erkennung

Nach dem ersten echten Lauf waren von 34 aufgenommenen Stellen **12
Fehltreffer** (Bürosachbearbeitung, Anwendungsentwicklung, Ingenieurstellen,
ein Crossmedia-Redakteur). Alle sind jetzt ausgeschlossen. **Rechne damit, dass
Randfälle bleiben** — dafür gibt es den 🗑-Knopf.

62 % der Stellen hatten zunächst keine erkannte Frist. Nach dem Fix an
`FRIST_RE` wurden drei sofort gerettet; der Rest sind Beratungshäuser, die
laufend ohne Frist ausschreiben. Das ist korrekt.

---

## 14. Was offen ist

Nach Nutzen geordnet. Nichts davon ist dringend.

### Mehr finden

- **Interamt vollständig lesen.** 25 Runden lesen 260 von 828. Beim ersten Lauf
  85 Runden einstellen; danach genügt der Standard, weil Neues oben steht.
- **Die großen Beratungen fehlen** — Capgemini, Deloitte, KPMG, adesso,
  Cassini, Materna. Ihre Stellensuche läuft nur über JavaScript-Portale ohne
  feste Adresse. Der Hebel wäre die Jobsuche-Schnittstelle der Bundesagentur
  für Arbeit (`rest.arbeitsagentur.de`), die aber mit 403 antwortet und einen
  Schlüssel bräuchte.
- **Drei Portale ohne Stellen-URL**: Landeshauptstadt Potsdam, Berlin Partner,
  Kassenärztliche Bundesvereinigung. Titel und Eckdaten stimmen, aber „Im
  Browser" und das Archiv-PDF treffen die Übersicht statt der Stelle.

### Übersicht verbessern

- **Dubletten zwischen den Quellen.** Dieselbe Stelle kann auf Interamt *und*
  im Berliner Portal stehen. Aktuell nachweislich null Dubletten — deshalb
  bewusst noch nicht gebaut. Sobald Interamt vollständig läuft, erneut messen.
- **Erkennen, dass eine Stelle vom Portal verschwunden ist.** `geprueft_am`
  liegt vor. Geringer Nutzen, weil das Archiv-PDF das Problem schon löst.

### Vielleicht

- **Anschreiben erzeugen.** Das Briefing liefert die Bausteine dafür schon
  (Anforderung → Beleg, Elefant im Raum). Fehlt ein Textgerüst und die
  Übergabe an ein Textprogramm.

---

## 15. Wenn du etwas ändern willst

### Grundsätze dieses Projekts

1. **Nichts erfinden.** Keine Arbeitgeber, keine URLs, keine Zahlen ohne
   Prüfung. Jede Adresse im Register wurde wirklich abgerufen.
2. **Ehrlich berichten.** Wenn eine Seite nichts liefert, steht das so da —
   mit Begründung. Siehe `arbeitgeber.NICHT_AUFGENOMMEN`.
3. **Messen statt schätzen.** Die Zahlen in Abschnitt 13 stammen aus echten
   Läufen. Wer etwas ändert, misst die Wirkung.
4. **Lieber ein kurzes ehrliches Register als Einträge, die nie etwas
   liefern.**
5. **Was der Mensch entschieden hat, rührt das Programm nicht an.** Status,
   Notizen, Favoriten, von Hand erfasste Stellen.

### Wo du anfängst

| Du willst … | Datei |
|---|---|
| andere Stellen finden | `einordnung.py` (Stichworte, Ausschlüsse) — oder im Fenster unter „Berufsfelder" |
| die Sortierung ändern | im Fenster unter „Gewichtung" |
| einen Arbeitgeber ergänzen | `arbeitgeber.py` |
| eine neue Quelle anbinden | `quelle_berlin.py` als Muster, dann in `suche.py` einhängen |
| am Aussehen schrauben | `oberflaeche.py` (Farben, Bausteine) |
| eine Ansicht ändern | `stellenradar.py` |
| das Briefing anders aufbauen | `briefing.py` (`SYSTEMTEXT`, `ANWEISUNG`) |

### Vor dem Ausliefern

1. `--selftest` und `--guitest` grün
2. Bei Änderungen an den Quellen: ein echter Lauf gegen mindestens eine Quelle
3. Bei Änderungen an der Oberfläche: Fenster wirklich starten, nicht nur testen
4. Paket neu bauen und prüfen, dass keine `.db` und keine `.log` mitwandert

---

## Anhang: Weiterführende Dateien

| Datei | Inhalt |
|---|---|
| `README.md` | ausführliche Bedienungs- und Funktionsbeschreibung |
| `LIESMICH.txt` | Kurzanleitung ohne Fachbegriffe |
| `arbeitgeber.py` | das Register, unten `NICHT_AUFGENOMMEN` mit Begründungen |
| `konfiguration.py` | alle Standardwerte für Felder, Gewichte und Profil |

